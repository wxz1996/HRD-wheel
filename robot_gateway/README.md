# Robot Gateway (MVP)

一个可运行的机器人端网关（FastAPI），与云端 Observer Service 对齐，支持：

- 技能执行闭环（HTTP + WebSocket）
- WebRTC 实时视频（机器人端作为 WebRTC server）
- Snapshot 抓帧接口（`/snapshot`，JPEG bytes）
- 本地 artifacts 静态文件托管
- ROS2 可选接入（不可用时自动 fallback）

## 1. 完整系统架构

### 1.1 总体架构（逻辑视图）

```text
┌──────────────────────────────────────────────────────────────────┐
│                        Cloud: Observer Service                  │
│  - follow_run 轮询 /runs/{run_id}                               │
│  - 调用 /snapshot 获取 JPEG                                     │
│  - 通过 /monitor/stream_info 获取 /webrtc/offer /debug/webrtc   │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTP / WS / WebRTC
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Robot Gateway (FastAPI, :8000)               │
│                                                                  │
│  REST API                                                        │
│   - POST /skills/{skill}:run                                    │
│   - GET  /runs/{run_id}                                          │
│   - POST /runs/{run_id}:cancel                                   │
│   - GET  /snapshot                                                │
│   - POST /webrtc/offer                                            │
│   - POST /webrtc/{session_id}:close                              │
│   - GET  /webrtc/sessions, /debug/webrtc                         │
│                                                                  │
│  WS API                                                           │
│   - /ws/runs/{run_id} 推送 progress/status/artifact/log           │
│                                                                  │
│  Internal Components                                              │
│   - app/main.py：路由与编排                                        │
│   - app/models.py：Envelope/请求/事件模型                          │
│   - app/run_store.py：run 生命周期与取消                           │
│   - app/ws_manager.py：run 级别 WS 广播                           │
│   - app/skills/*：move_to/capture_image/get_status               │
│   - app/snapshot.py：JPEG 抓帧                                    │
│   - app/webrtc/*：WebRTC 会话管理与视频轨                          │
│                                                                  │
│  Storage                                                          │
│   - ./artifacts 挂载到 /artifacts                                │
│   - capture_image -> ./artifacts/img/{run_id}.jpg               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                ┌───────────────┴────────────────┐
                ▼                                ▼
       ┌───────────────────────┐        ┌───────────────────────────┐
       │ ROS2 Source (optional)│        │ Fallback Frame Generator  │
       │ rclpy + sensor_msgs   │        │ 生成带时间戳的模拟帧/JPEG  │
       │ + cv_bridge           │        │ (无 ROS2 时自动启用)       │
       └───────────────────────┘        └───────────────────────────┘
```

### 1.2 目录与职责（实现视图）

```text
robot_gateway/
  app/
    main.py                # FastAPI 入口与所有路由
    config.py              # 环境变量读取（默认 topic/分辨率/fps/STUN）
    models.py              # Envelope、Artifact、Error、请求/响应/事件模型
    run_store.py           # 内存 run 状态管理 + cancel_event
    ws_manager.py          # WebSocket 连接与事件广播
    skills/
      move_to.py           # 异步 move_to（进度、可取消）
      capture_image.py     # 生成 artifact 图片并返回 URL
      get_status.py        # mock 电量/模式
    adapters/
      base.py              # 机器人适配抽象
      mock_adapter.py      # mock 适配实现
    webrtc/
      manager.py           # aiortc RTCPeerConnection session 生命周期
      tracks.py            # VideoStreamTrack -> av.VideoFrame
      ros_source.py        # ROS2 订阅帧源 + fallback 帧源
    snapshot.py            # /snapshot JPEG 输出（复用帧源）
  artifacts/
    img/
  static/
    webrtc_debug.html      # 浏览器端 WebRTC 调试页面
  tests/
    test_api.py            # API 行为测试
```

### 1.3 关键数据流（时序视图）

#### A) Skill 执行闭环（以 move_to 为例）

```text
Observer/Client -> POST /skills/move_to:run
Robot Gateway:
  1) run_store.create() 生成 run_id, status=CREATED
  2) 后台任务 execute_move_to() -> status=RUNNING
  3) 周期性通过 ws_manager.publish() 推送 progress
  4) 结束后 status=SUCCEEDED（或 CANCELED/FAILED）
Observer/Client:
  - 轮询 GET /runs/{run_id}
  - 或订阅 ws://.../ws/runs/{run_id}
```

#### B) 抓图与 artifact

```text
Client -> POST /skills/capture_image:run
Robot Gateway:
  1) 生成 JPEG 到 ./artifacts/img/{run_id}.jpg
  2) 返回 Envelope.artifacts[0].url =
     http://<robot_host>:8000/artifacts/img/{run_id}.jpg
  3) 同时通过 WS 推送 artifact_created/status_changed
```

#### C) Snapshot（Observer 对齐接口）

```text
Observer -> GET /snapshot?camera_topic=...&width=...&height=...
Robot Gateway:
  - ROS2 可用：从 topic 取最新帧并编码 JPEG
  - ROS2 不可用：fallback 生成伪帧并编码 JPEG
返回：image/jpeg bytes（非 JSON）
```

#### D) WebRTC 视频流

```text
Browser/Observer:
  1) 创建本地 offer SDP
  2) POST /webrtc/offer {sdp,type,camera_topic,width,height,fps}
Robot Gateway:
  3) 创建 RTCPeerConnection + CameraVideoTrack
  4) setRemoteDescription(offer)
  5) createAnswer + setLocalDescription(answer)
  6) 返回 {sdp,type:"answer",session_id}
Browser:
  7) setRemoteDescription(answer) 开始收流
  8) 结束时 POST /webrtc/{session_id}:close
```

### 1.4 状态机

`RunStatus`: `CREATED -> RUNNING -> SUCCEEDED|FAILED|CANCELED`

- `move_to`：`CREATED -> RUNNING -> SUCCEEDED`（可在 RUNNING 时 cancel -> CANCELED）
- `capture_image/get_status`：通常快速收敛到 `SUCCEEDED`

### 1.5 部署与网络边界

- 服务监听：`0.0.0.0:8000`（通过 uvicorn 启动参数控制）
- 静态文件：`/artifacts/*` 对外可访问（用于云端直接拉取图片）
- WebRTC：默认 host candidates；可用 `STUN_SERVER` 增强跨网段连通
- 建议在机器人设备上放行：`8000/tcp`（HTTP/WS/WebRTC 信令）

## 2. 快速启动

> Python 3.10+

```bash
cd robot_gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

服务默认地址：`http://localhost:8000`

## 3. 环境变量

- `ROBOT_PORT`（默认 `8000`，用于生成 artifact URL）
- `DEFAULT_CAMERA_TOPIC`（默认 `/camera/image_raw`）
- `DEFAULT_WIDTH`（默认 `640`）
- `DEFAULT_HEIGHT`（默认 `480`）
- `DEFAULT_FPS`（默认 `15`）
- `STUN_SERVER`（可选，例如 `stun:stun.l.google.com:19302`）

示例：

```bash
export ROBOT_PORT=8000
export DEFAULT_CAMERA_TOPIC=/camera/image_raw
export DEFAULT_WIDTH=640
export DEFAULT_HEIGHT=480
export DEFAULT_FPS=15
export STUN_SERVER=stun:stun.l.google.com:19302
```

## 4. API 使用（curl）

### 4.1 move_to

```bash
curl -X POST 'http://localhost:8000/skills/move_to:run' \
  -H 'content-type: application/json' \
  -d '{"location":"dock","timeout_seconds":10}'
```

### 4.2 查询 run 状态

```bash
curl 'http://localhost:8000/runs/<run_id>'
```

### 4.3 取消 run

```bash
curl -X POST 'http://localhost:8000/runs/<run_id>:cancel'
```

### 4.4 capture_image

```bash
curl -X POST 'http://localhost:8000/skills/capture_image:run' \
  -H 'content-type: application/json' \
  -d '{"camera":"front"}'
```

### 4.5 snapshot

```bash
curl 'http://localhost:8000/snapshot?camera_topic=/camera/image_raw&width=640&height=480' --output snap.jpg
```

## 5. WebSocket 订阅 run 事件

```text
ws://localhost:8000/ws/runs/{run_id}
```

事件格式：

```json
{
  "run_id": "...",
  "event": "progress|status_changed|artifact_created|log",
  "status": "CREATED|RUNNING|SUCCEEDED|FAILED|CANCELED",
  "percent": 10,
  "message": "...",
  "telemetry": {}
}
```

## 6. WebRTC 调试

浏览器打开：

- `http://localhost:8000/debug/webrtc`

页面中可输入 `camera_topic` 后连接。

API：

- `POST /webrtc/offer`
- `POST /webrtc/{session_id}:close`
- `GET /webrtc/sessions`

## 7. 与云端 Observer 对接

- 设置云端：`ROBOT_BASE_URL=http://<robot_host>:8000`
- Observer 会调用：
  - `/snapshot?camera_topic=...&width=...&height=...`
  - `/runs/{run_id}`（需至少含 `status`）
- Observer `/monitor/stream_info` 可返回：
  - `/webrtc/offer`
  - `/debug/webrtc`

## 8. ROS2 适配说明

- 若环境可导入 `rclpy + sensor_msgs + cv_bridge`，将尝试用 ROS2 topic 帧源。
- 若 ROS2 不可用，自动 fallback 生成带时间戳的伪视频帧。
- Snapshot/WebRTC 在无 ROS2 时也可运行。

## 9. aiortc/av 依赖排错

`aiortc` 依赖 `av`，在某些系统可能需要 FFmpeg 相关库。
若安装失败，请先安装系统依赖（按你的发行版选择）。
