# Mapping Module

这是机器人建图子模块的内部说明，不作为独立 Codex skill 使用。涉及该模块时，应通过 `$robot-skill` 路由进入。

## Planned Scope

- 启动建图任务
- 停止建图任务
- 保存地图元数据与结果回执
- 同步建图状态到 gateway

## Status

- 已提供 MQTT service 骨架，便于后续接入真实建图流程

## Key Files

- `../common/mqtt.py`
- `scripts/mqtt_mapping_service.py`
