# Robot Subskills

`robot-skill` 作为聚合入口时，按下面的路由表选择子 skill。

## Routing Table

### `camera_monitor`

- 路径: `../../robot_services/camera_monitor/MODULE.md`
- 适用任务: MQTT 视频接入、帧缓存、视频状态、MJPEG 输出、`/api/video/status`、`/api/video/stream`
- 关键实现: `../../robot_services/camera_monitor/scripts/mqtt_video_service.py`
- 当前状态: 已有实现入口

### `manipulation`

- 路径: `../../robot_services/manipulation/MODULE.md`
- 适用任务: 机械臂、抓取、放置、操作任务编排、动作结果回执
- 当前状态: 预留说明，尚未形成完整实现

### `motion`

- 路径: `../../robot_services/motion/MODULE.md`
- 适用任务: 底盘运动控制、速度限制、安全约束、动作反馈
- 当前状态: 已有 MQTT service 骨架，可继续接入底盘控制

### `speech`

- 路径: `../../robot_services/speech/MODULE.md`
- 适用任务: ASR、TTS、语音指令路由、语音到动作映射
- 当前状态: 预留说明，尚未形成完整实现

### `vision`

- 路径: `../../robot_services/vision/MODULE.md`
- 适用任务: 目标检测、跟踪、识别结果结构化、视觉结果与 gateway 对接
- 当前状态: 预留说明，尚未形成完整实现

### `mapping`

- 路径: `../../robot_services/mapping/MODULE.md`
- 适用任务: 启动建图、停止建图、保存地图、同步建图状态
- 当前状态: 已有 MQTT service 骨架，尚未接入真实建图流程

### `point_navigation`

- 路径: `../../robot_services/point_navigation/MODULE.md`
- 适用任务: 导航到命名点位、取消导航、接收导航状态与到点回执
- 当前状态: 已有 MQTT service 骨架，尚未接入真实导航流程

## Multi-skill Cases

- 视频识别链路: 同时查看 `camera_monitor` 和 `vision`
- 语音控制机器人: 同时查看 `speech` 和 `motion` 或 `manipulation`
- 厨房巡检任务: 通常同时查看 `point_navigation`、`camera_monitor`、`vision`
- 前端机器人状态页问题: 先确认是 gateway API/上下文问题，还是具体机器人子能力问题，再决定是否读取子 skill
