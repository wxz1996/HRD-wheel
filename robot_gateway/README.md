# Robot Gateway (MVP)

一个可运行的机器人端网关（FastAPI），与云端 Observer Service 对齐，支持：

- 技能执行闭环（HTTP + WebSocket）
- WebRTC 实时视频（机器人端作为 WebRTC server）
- Snapshot 抓帧接口（`/snapshot`，JPEG bytes）
- 本地 artifacts 静态文件托管
- ROS2 可选接入（不可用时自动 fallback）

## 1. 快速启动

> Python 3.10+

```bash
cd robot_gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

服务默认地址：`http://localhost:8000`

## 2. 环境变量

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

## 3. API 使用（curl）

### 3.1 move_to

```bash
curl -X POST 'http://localhost:8000/skills/move_to:run' \
  -H 'content-type: application/json' \
  -d '{"location":"dock","timeout_seconds":10}'
```

### 3.2 查询 run 状态

```bash
curl 'http://localhost:8000/runs/<run_id>'
```

### 3.3 取消 run

```bash
curl -X POST 'http://localhost:8000/runs/<run_id>:cancel'
```

### 3.4 capture_image

```bash
curl -X POST 'http://localhost:8000/skills/capture_image:run' \
  -H 'content-type: application/json' \
  -d '{"camera":"front"}'
```

### 3.5 snapshot

```bash
curl 'http://localhost:8000/snapshot?camera_topic=/camera/image_raw&width=640&height=480' --output snap.jpg
```

## 4. WebSocket 订阅 run 事件

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

## 5. WebRTC 调试

浏览器打开：

- `http://localhost:8000/debug/webrtc`

页面中可输入 `camera_topic` 后连接。

API：

- `POST /webrtc/offer`
- `POST /webrtc/{session_id}:close`
- `GET /webrtc/sessions`

## 6. 与云端 Observer 对接

- 设置云端：`ROBOT_BASE_URL=http://<robot_host>:8000`
- Observer 会调用：
  - `/snapshot?camera_topic=...&width=...&height=...`
  - `/runs/{run_id}`（需至少含 `status`）
- Observer `/monitor/stream_info` 可返回：
  - `/webrtc/offer`
  - `/debug/webrtc`

## 7. ROS2 适配说明

- 若环境可导入 `rclpy + sensor_msgs + cv_bridge`，将尝试用 ROS2 topic 帧源。
- 若 ROS2 不可用，自动 fallback 生成带时间戳的伪视频帧。
- Snapshot/WebRTC 在无 ROS2 时也可运行。

## 8. aiortc/av 依赖排错

`aiortc` 依赖 `av`，在某些系统可能需要 FFmpeg 相关库。
若安装失败，请先安装系统依赖（按你的发行版选择）。

