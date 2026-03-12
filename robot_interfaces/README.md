# robot_interfaces (ROS2 风格接口声明, stub only)

本目录仅声明 HRT MVP 所需通信接口，不包含真实机器人执行逻辑。

- `messages/`: 消息字段定义（JSON schema 风格）
- `topics/`: Topic 声明（上行状态/视觉/日志 + 下行控制）
- `services/`: Service 声明（可选）
- `adapters/`: 网关适配骨架说明
