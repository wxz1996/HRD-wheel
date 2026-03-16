# gateway_agent 运行逻辑说明

本文档说明 `gateway_agent` 在当前 MVP 中如何运行，以及它和 `web_fronted`、`robot_agent` 的交互关系。

## 1. 角色定位

`gateway_agent` 是前后端之间的网关层，当前主要职责：

- 对外提供 HTTP API（登录、状态、视频相关接口）
- 提供 WebSocket 通道（状态/日志/识别结果/控制 ACK）
- 从 MQTT 订阅机器人视频帧并转成 MJPEG 给前端
- 提供 token 鉴权与基础安全响应头

当前版本中，`gateway_agent` 不直接连接 ROS2。

## 1.1 skills 目录结构

为支持后续机器人能力开发与 Codex 路由，网关目录按语义拆分：

- `skills/robot-skill/`：Codex 聚合入口 skill，负责路由到对应机器人子模块
- `robot_services/camera_monitor/`：视频监控内部模块（含 `MODULE.md` 与 `scripts/mqtt_video_service.py`）
- `robot_services/common/`：机器人服务共享基础设施（如 MQTT 连接与生命周期抽象）
- `robot_services/motion/`：运动控制内部模块（含 `scripts/mqtt_motion_service.py` 骨架）
- `robot_services/mapping/`：建图内部模块（含 `scripts/mqtt_mapping_service.py` 骨架）
- `robot_services/point_navigation/`：导航到点内部模块（含 `scripts/mqtt_point_navigation_service.py` 骨架）
- `robot_services/speech/`：语音内部模块（预留）
- `robot_services/vision/`：视觉算法内部模块（含 `scripts/mqtt_vision_service.py` 骨架）
- `robot_services/manipulation/`：操作/机械臂内部模块（含 `scripts/mqtt_manipulation_service.py` 骨架）
- `gateway_context_service.py`：网关侧上下文（状态/日志/识别）

## 2. 进程生命周期

入口文件：`gateway_agent/main.py`

- 启动时：
  - 初始化 FastAPI
  - 注册 CORS
  - 挂载 API 路由 `/api/*`
  - 挂载 WS 路由 `/ws/*`
  - 启动 MQTT 视频服务（`get_mqtt_video_service().start()`）
- 关闭时：
  - 停止 MQTT 视频服务（`get_mqtt_video_service().stop()`）

## 3. 与 Web 的交互

### 3.1 HTTP 交互

主要接口（`gateway_agent/api/routes.py`）：

- `POST /api/login`
  - 入参：`{ account, password }`
  - 返回：`token`（Bearer）
- `GET /api/me`
- `GET /api/robot/summary`
- `GET /api/ar/bootstrap`
- `POST /api/ar/recognition/toggle`
- `POST /api/ar/selection`
- `GET /api/navigation/waypoints`
- `GET /api/navigation/status`
- `POST /api/navigation/goals`
- `POST /api/navigation/goals/{goal_id}/cancel`
- `GET /api/vision/status`
- `GET /api/manipulation/status`
- `POST /api/tasks/monitor-gas-stove`
- `POST /api/tasks/inspect-gas-stove`
- `GET /api/video/status`
- `POST /api/video/token`（签发短时视频 token）
- `GET /api/video/stream?token=...`（MJPEG）

鉴权逻辑（`gateway_agent/security.py`）：

- 除 `/api/login` 外，REST 默认要求 `Authorization: Bearer <token>`
- `/api/video/stream` 支持 query token（适配 `<img src=...>`）

### 3.2 WebSocket 交互

WS 路由（`gateway_agent/ws/endpoints.py`）：

- `/ws/state`：周期推送状态
- `/ws/logs`：周期推送日志
- `/ws/vision`：周期推送识别结果
- `/ws/control`：接收控制消息，经 MQTT 下发后回 ACK

说明：

- WS 鉴权使用 query token：`/ws/xxx?token=<bearer-token>`
- `/ws/control` 会对输入做限幅，并向 `HRT_MQTT_MOTION_CMD_TOPIC` 发布控制命令
- 若机器人在 `HRT_MQTT_MOTION_ACK_TOPIC` 上快速返回 ACK，网关会把 ACK 一并透传给前端；否则先返回 `ackPending=true`

## 4. 与 Robot 的交互

### 4.1 当前已打通链路（视频）

`gateway_agent` 通过 MQTT 订阅 `robot_agent` 发布的视频 topic：

- 默认 topic：`hrt/camera/color/jpeg`
- 环境变量：`HRT_MQTT_VIDEO_TOPIC`
- 配置入口：`gateway_agent/robot_services/camera_monitor/scripts/mqtt_video_service.py`

`mqtt_video_service` 支持两种消息格式：

- 原始 JPEG 二进制（推荐）
- JSON 包裹 base64（兼容）

订阅到帧后，写入内存帧缓存 `FrameHub`，再由：

- `GET /api/video/stream` 按 MJPEG 连续输出给前端
- `GET /api/video/status` 返回连接与帧计数状态

### 4.2 当前链路（机器人控制）

当前 MVP 中，`gateway_agent` 已经把控制指令通过 MQTT 命令 topic 下发到底盘服务约定 topic，但是否真正执行仍取决于机器人侧是否消费该 topic 并回 ACK。

也就是说：

- 视频：`robot_agent -> MQTT -> gateway_agent -> web_fronted`（已打通）
- 控制：`web_fronted -> gateway_agent /ws/control -> MQTT cmd topic -> robot`（网关侧已打通）
- 点位导航：`gateway_agent /api/navigation/goals -> MQTT nav cmd topic -> robot`（网关侧入口已就绪）
- 高层巡检任务：`gateway_agent /api/tasks/monitor-gas-stove -> navigation + vision`（网关侧编排已就绪）
- 条件巡检任务：`gateway_agent /api/tasks/inspect-gas-stove -> navigation + vision + conditional manipulation`（网关侧编排已就绪）

## 5. 运行时配置（核心）

`gateway_agent` 常用环境变量：

- `HRT_MQTT_HOST`：MQTT 地址（默认 `127.0.0.1`）
- `HRT_MQTT_PORT`：MQTT 端口（默认 `1883`）
- `HRT_MQTT_VIDEO_TOPIC`：视频 topic（默认 `hrt/camera/color/jpeg`）
- `HRT_MQTT_MOTION_CMD_TOPIC`：控制命令 topic（默认 `hrt/robot/motion/cmd`）
- `HRT_MQTT_MOTION_ACK_TOPIC`：控制 ACK topic（默认 `hrt/robot/motion/ack`）
- `HRT_MQTT_MAPPING_CMD_TOPIC`：建图命令 topic（默认 `hrt/robot/mapping/cmd`）
- `HRT_MQTT_MAPPING_STATUS_TOPIC`：建图状态 topic（默认 `hrt/robot/mapping/status`）
- `HRT_MQTT_NAV_CMD_TOPIC`：导航命令 topic（默认 `hrt/robot/navigation/cmd`）
- `HRT_MQTT_NAV_STATUS_TOPIC`：导航状态 topic（默认 `hrt/robot/navigation/status`）
- `HRT_MQTT_VISION_CMD_TOPIC`：视觉任务命令 topic（默认 `hrt/robot/vision/cmd`）
- `HRT_MQTT_VISION_STATUS_TOPIC`：视觉任务状态 topic（默认 `hrt/robot/vision/status`）
- `HRT_MQTT_MANIPULATION_CMD_TOPIC`：操作命令 topic（默认 `hrt/robot/manipulation/cmd`）
- `HRT_MQTT_MANIPULATION_STATUS_TOPIC`：操作状态 topic（默认 `hrt/robot/manipulation/status`）
- `HRT_MQTT_USERNAME` / `HRT_MQTT_PASSWORD`：MQTT 认证（可选）
- `HRT_ALLOWED_ORIGINS`：CORS 白名单（逗号分隔）
- `HRT_DEMO_ACCOUNT` / `HRT_DEMO_PASSWORD`：登录账号密码
- `HRT_TOKEN_SECRET`：token 签名密钥

## 6. 最小链路自检

1. 网关健康检查：

```bash
curl -s http://127.0.0.1:8000/healthz
```

2. 登录拿 token：

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/login \
  -H 'content-type: application/json' \
  -d '{"account":"demo","password":"demo123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
```

3. 看视频状态：

```bash
curl -s http://127.0.0.1:8000/api/video/status -H "Authorization: Bearer $TOKEN"
```

当 `frameSeq > 0` 时表示网关已持续收到机器人视频帧。

4. 看导航点位：

```bash
curl -s http://127.0.0.1:8000/api/navigation/waypoints -H "Authorization: Bearer $TOKEN"
```

5. 发起厨房燃气灶巡检任务：

```bash
curl -s -X POST http://127.0.0.1:8000/api/tasks/monitor-gas-stove \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"targetName":"kitchen"}'
```

6. 发起带条件分支的厨房燃气灶巡检任务：

```bash
curl -s -X POST http://127.0.0.1:8000/api/tasks/inspect-gas-stove \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"targetName":"kitchen","smokeLevel":"high"}'
```
