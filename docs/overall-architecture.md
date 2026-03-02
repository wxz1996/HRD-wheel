# 机器人协作平台整体架构（第一版）

> 目标：你先做一版可以落地的总体架构，后续再细化到接口和部署。

---

## 1. 总体分层

建议采用 **3 层架构**：

1. **机器人本体层（Jetson Orin NX + ROS 2）**
   - 负责实时感知、状态管理、机械臂控制与反馈闭环。
2. **边云通信层（MQTT + JSON）**
   - 负责可靠、可扩展的数据上行与控制下行。
3. **云端平台层（接入/存储/处理/应用）**
   - 负责 topic 监听、持久化、规则处理、任务编排、Web/API 服务。

这样能把实时控制留在本地，把重计算与多机器人协同放到云端。

---

## 2. 机器人本体中控（ROS 2）

### 2.1 本体功能模块

Jetson 上建议拆分以下 ROS 2 节点（Node）：

- **robot_state_manager**
  - 汇总机器人运行状态：电量、模式、故障码、网络状态、任务状态。
- **sensor_fusion_node**
  - 接入相机/雷达/IMU/编码器等传感器，输出融合状态。
- **arm_controller_node**
  - 执行机械臂控制算法（轨迹规划、逆解、PID/模型控制），输出控制指令。
- **arm_feedback_node**
  - 回传关节角、力矩、末端位姿、执行误差与异常告警。
- **edge_mqtt_bridge**
  - 把 ROS 2 topic 与 MQTT topic 做双向映射（JSON 编码/解码）。

### 2.2 ROS 2 topic 设计建议

建议先定义一组稳定 topic（示例）：

- `/robot/state`：机器人总体状态（1~10 Hz）
- `/robot/sensors/fused`：传感器融合输出（10~50 Hz）
- `/arm/command`：机械臂控制指令（按需触发）
- `/arm/feedback`：机械臂反馈（10~100 Hz）
- `/robot/event`：事件与告警（异步）

> 高频原始数据（例如图像流）不建议直接上 MQTT+JSON，可在本体侧先抽特征或压缩后再上传。

### 2.3 本地实时性与安全

- 控制闭环必须在本地完成，避免云端网络抖动影响安全。
- 建议配置“失联保护”策略：
  - 与云端断开后，机器人进入本地安全模式；
  - 机械臂执行减速/保持/回零等策略；
  - 本地继续记录日志，恢复后补传。

---

## 3. 边云通信层（MQTT + JSON）

### 3.1 通信模式

- **上行（机器人 -> 云）**：状态、传感器摘要、机械臂反馈、告警事件。
- **下行（云 -> 机器人）**：任务下发、参数更新、模式切换、远程控制指令。

推荐 MQTT topic 命名（按 robot_id 分区）：

- `robot/{robot_id}/telemetry/state`
- `robot/{robot_id}/telemetry/sensor`
- `robot/{robot_id}/telemetry/arm_feedback`
- `robot/{robot_id}/event`
- `robot/{robot_id}/cmd/arm`
- `robot/{robot_id}/cmd/system`

### 3.2 QoS 与可靠性建议

- 状态类：QoS 0 或 1（可容忍少量丢包）
- 控制命令：QoS 1（至少一次），命令需带 `cmd_id` 防重放
- 关键事件：QoS 1 + 持久会话 + Retain（按需）

### 3.3 JSON 消息规范（最小字段）

建议统一 envelope：

```json
{
  "msg_id": "uuid",
  "robot_id": "RBT-001",
  "ts": 1730000000000,
  "type": "arm_feedback",
  "schema_ver": "1.0",
  "payload": {}
}
```

补充建议：

- 所有时间戳统一 UTC 毫秒。
- 添加 `trace_id` 用于跨服务追踪。
- 版本升级时保持向后兼容（新增字段不破坏旧解析）。

---

## 4. 云端服务器架构

### 4.1 云端核心服务

1. **MQTT 接入服务（Broker + Auth）**
   - 负责连接管理、鉴权、topic ACL。
2. **Topic 监听/消费服务（Ingestion Service）**
   - 订阅机器人 topic，做 JSON 校验、清洗、标准化。
3. **数据存储服务**
   - 时序数据：InfluxDB/TimescaleDB（状态、反馈）
   - 事件数据：PostgreSQL（告警、任务、审计）
   - 大文件：对象存储（图片/日志包）
4. **处理与规则引擎**
   - 异常检测、阈值告警、任务编排、统计计算。
5. **应用服务层（API + Web）**
   - 提供看板、机器人管理、任务调度、远程维护接口。

### 4.2 推荐数据流

1. 机器人 ROS 2 节点产出 topic。
2. `edge_mqtt_bridge` 转为 JSON 发到 MQTT Broker。
3. 云端 ingestion 服务订阅后写入数据库。
4. 规则引擎消费数据触发告警/动作。
5. Web/API 展示并支持下发控制命令。
6. 控制命令经 MQTT 下发到机器人，再映射回 ROS 2 topic。

---

## 5. 安全与运维

- MQTT 开启 TLS，设备证书双向认证（mTLS）。
- 每台机器人独立凭证与最小 ACL 权限。
- 命令消息加签或附带 nonce，防止重放攻击。
- 全链路日志：设备日志、消息日志、操作审计日志。
- 提供 OTA/参数远程更新，但必须有灰度和回滚策略。

---

## 6. 第一阶段落地范围（MVP）

建议你先做可运行 MVP：

1. Jetson 侧：
   - 跑通 ROS 2 节点 + `edge_mqtt_bridge`
   - 至少上报 `/robot/state` 与 `/arm/feedback`
2. 云端侧：
   - 搭建 MQTT Broker（如 EMQX/Mosquitto）
   - 实现 ingestion 服务（订阅 + 入库）
   - 提供一个最小 Web 看板（在线状态 + 最近告警）
3. 命令闭环：
   - 从 Web 下发一个机械臂动作命令
   - 机器人执行并回传结果

当 MVP 跑通后，再逐步增强：多机器人调度、数字孪生、智能故障诊断。

---

## 7. 你下一步可以马上做的事

- 明确 10~20 个核心消息 schema（状态、反馈、告警、命令）。
- 先固定 topic 命名与 QoS 策略，避免后期频繁改协议。
- 用 docker-compose 一次启动 Broker + DB + Ingestion + Web。
- 在 Jetson 上实现 ROS2 <-> MQTT 的桥接最小闭环 Demo。

如果你愿意，我下一步可以直接给你：
1) 一份可执行的消息 schema 清单；
2) ROS2 与 MQTT topic 对照表；
3) MVP 的 docker-compose 与服务目录结构建议。
