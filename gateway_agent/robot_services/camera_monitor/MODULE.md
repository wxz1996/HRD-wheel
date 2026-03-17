# Camera Monitor Module

这是机器人视频监控子模块的内部说明，不作为独立 Codex skill 使用。涉及该模块时，应通过 `$robot-skill` 路由进入。

## Scope

- 调整 MQTT 视频 topic、连接参数、认证
- 调整 JPEG 和 JSON(base64) 两种视频消息解析逻辑
- 调整帧缓存策略 `FrameHub` 与状态统计
- 排查 `/api/video/status` 与 `/api/video/stream` 问题

## Boundaries

- 仅负责视频链路，不处理机器人底盘控制
- 与 Web 的交互通过 API 层完成，不在这里定义路由

## Key Files

- `../common/mqtt.py`
- `scripts/mqtt_video_service.py`
