# HRD-wheel

机器人协作平台（Robot Collaboration Platform）架构草案。

## 平台目标

构建一个由**本体中控（Jetson Orin NX, ARM）**与**云端服务器**组成的双层系统：

- 本体中控负责实时控制与状态采集（ROS 2 生态内闭环）。
- 云端服务器负责数据接入、存储、分析、可视化和远程运维。
- 两端通过 **MQTT + JSON** 做跨网络通信，形成“边缘实时 + 云端智能”的协作体系。

详细设计见：`docs/overall-architecture.md`。
