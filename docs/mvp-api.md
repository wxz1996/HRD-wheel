# HRT v0.0.1 MVP 接口说明

## 鉴权与安全

- 登录接口：`POST /api/login`
- 除 `POST /api/login` 外，REST 接口需要 `Authorization: Bearer <token>`
- WebSocket 需要 `?token=<token>` 查询参数
- CORS 默认仅允许本地前端：`http://localhost:3000`, `http://127.0.0.1:3000`
- 控制通道会对摇杆范围做限幅（x/y 自动限制到 `[-1, 1]`）

## REST

- `POST /api/login`
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
- `GET /api/video/stream?token=<video-token>`

## WebSocket

- `/ws/state`：推送状态
- `/ws/logs`：推送日志
- `/ws/vision`：推送识别结果
- `/ws/control`：接收摇杆控制，经 MQTT 命令 topic 下发并 ACK

## 视频流

- 当前使用 `ROS2 Image Topic -> MQTT JPEG -> Gateway MJPEG` 链路
- 前端通过 `/api/video/stream` 拉取 MJPEG 并实时显示
- 默认 ROS2 topic：`/camera/color/image_raw`（RealSense）
- 默认 MQTT topic：`hrt/camera/color/jpeg`
- 默认 MQTT broker：`HRT_MQTT_HOST=127.0.0.1`, `HRT_MQTT_PORT=1883`

## WebRTC vs MQTT 评估

- 当前阶段（底盘暂不可控，先打通视频）推荐：`MQTT + MJPEG`
- 选择理由：
  - 实现快，和现有 `gateway` 架构兼容
  - 便于排障（topic 可直接观测）
  - 单路 RGB（30Hz）足够支撑 MVP 可视化
- 后续如果目标是更低延迟/更高并发观看，再升级 `WebRTC` 更合适（可保留 MQTT 做状态与控制）

## 模式

- 运行态内存状态模式：默认，可独立演示
