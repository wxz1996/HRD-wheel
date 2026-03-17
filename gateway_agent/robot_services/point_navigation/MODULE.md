# Point Navigation Module

这是机器人导航到点子模块的内部说明，不作为独立 Codex skill 使用。涉及该模块时，应通过 `$robot-skill` 路由进入。

## Planned Scope

- 下发导航目标点
- 取消当前导航任务
- 接收导航进度与到点状态
- 维护 waypoint 与业务点位映射

## Status

- 已提供 MQTT service 骨架，便于后续接入真实导航流程

## Key Files

- `../common/mqtt.py`
- `waypoints.py`
- `scripts/mqtt_point_navigation_service.py`
