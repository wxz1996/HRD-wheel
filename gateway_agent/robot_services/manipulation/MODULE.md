# Manipulation Module

这是机器人操作与机械臂子模块的内部说明，不作为独立 Codex skill 使用。涉及该模块时，应通过 `$robot-skill` 路由进入。

## Planned Scope

- 抓取与放置流程
- 操作任务编排
- 动作结果回执

## Status

- 已提供 MQTT service 骨架，便于后续接入真实操作动作

## Key Files

- `../common/mqtt.py`
- `scripts/mqtt_manipulation_service.py`
