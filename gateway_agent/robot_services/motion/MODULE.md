# Motion Module

这是机器人底盘运动子模块的内部说明，不作为独立 Codex skill 使用。涉及该模块时，应通过 `$robot-skill` 路由进入。

## Planned Scope

- 底盘控制指令下发
- 限幅与安全约束
- 控制回执与状态上报

## Status

- 已提供 MQTT service 骨架，便于后续接入真实底盘控制

## Key Files

- `../common/mqtt.py`
- `scripts/mqtt_motion_service.py`
