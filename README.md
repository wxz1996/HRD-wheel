# HRD-wheel

机器人协作平台（Robot Collaboration Platform）MVP。

## 已实现的 MVP 能力

1. **云端平台向机器人发送底盘指令**
   - 云端服务 `CloudServer` 默认发送 `twist=[0.1,0,0,0,0,0]` 到 MQTT 主题：`robot/{robot_id}/cmd/chassis`。
2. **本体层接收指令并调用 ROS2 导航适配层，返回状态**
   - 机器人服务 `RobotAgent` 订阅命令后调用 `Ros2Navigator.move_chassis()` 执行动作。
   - 执行过程会上报 `accepted` 与 `success/failed` 到 `robot/{robot_id}/status/nav`。
3. **云端接收回传并记忆**
   - 云端订阅状态主题后写入 SQLite（`mvp/data/cloud_memory.db`），可按 robot_id 查询历史状态。

详细总体架构见：`docs/overall-architecture.md`。

## 目录结构

- `mvp/cloud/server.py`: 云端指令下发 + 状态监听
- `mvp/cloud/memory_store.py`: 云端状态持久化（SQLite）
- `mvp/robot/agent.py`: 机器人命令处理与状态回传
- `mvp/robot/navigator.py`: ROS2 导航适配层（无 ROS2 时降级 mock）
- `mvp/common/schema.py`: MQTT JSON 消息结构

## 本地运行

### 1) 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 启动 MQTT Broker（示例）

```bash
docker run --rm -it -p 1883:1883 eclipse-mosquitto:2
```

### 3) 启动机器人侧

```bash
python -m mvp.robot.agent
```

### 4) 启动云端侧（自动发送 demo 指令）

```bash
python -m mvp.cloud.server
```

## 测试

```bash
pytest mvp/tests -q
```
