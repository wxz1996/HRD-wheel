# Vision Module

这是机器人视觉子模块的内部说明，不作为独立 Codex skill 使用。涉及该模块时，应通过 `$robot-skill` 路由进入。

## Planned Scope

- 目标检测与识别
- 多目标跟踪
- 识别结果结构化输出

## Status

- 已提供 MQTT service 骨架，便于后续接入真实视觉任务

## Key Files

- `../common/mqtt.py`
- `scripts/mqtt_vision_service.py`
