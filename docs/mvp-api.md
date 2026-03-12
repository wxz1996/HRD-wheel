# HRT v0.0.1 MVP 接口说明

## REST

- `POST /api/login`
- `GET /api/me`
- `GET /api/robot/summary`
- `GET /api/ar/bootstrap`
- `POST /api/ar/recognition/toggle`
- `POST /api/ar/selection`

## WebSocket

- `/ws/state`：推送状态
- `/ws/logs`：推送日志
- `/ws/vision`：推送识别结果
- `/ws/control`：接收摇杆控制并 ACK

## 模式

- mock 模式：默认，可独立演示
- adapter 模式：预留骨架（`gateway/robot_adapter/`）
