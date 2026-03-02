# MVP 运行说明（云端 <-> 机器人）

这份文档只关注“怎么跑起来”。

## 1. 功能闭环

当前 MVP 已实现：

1. 云端发送底盘指令（示例：`[0.1, 0, 0, 0, 0, 0]`）到机器人。
2. 机器人接收指令后调用导航适配层执行（ROS2 可接入，当前默认可 mock）。
3. 机器人上报执行状态（`accepted` / `success` / `failed`）给云端。
4. 云端接收状态并写入 SQLite 做“记忆”。

---

## 2. 环境准备

- Python 3.10+
- Docker（用于快速起 MQTT broker）

安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. 启动顺序（本地）

### Step A: 启动 MQTT Broker

```bash
docker run --rm -it -p 1883:1883 eclipse-mosquitto:2
```

> 保持该终端窗口运行。

### Step B: 启动机器人侧服务

新开终端：

```bash
source .venv/bin/activate
python -m mvp.robot.agent
```

机器人会订阅：`robot/RBT-001/cmd/chassis`。

### Step C: 启动云端侧服务

再开一个终端：

```bash
source .venv/bin/activate
python -m mvp.cloud.server
```

云端启动后会自动发送一次 demo 指令：`[0.1,0,0,0,0,0]`。

---

## 4. 运行结果验证

云端日志应看到类似输出：

- `sent command <cmd_id>`
- `stored status: accepted cmd=<cmd_id>`
- `stored status: success cmd=<cmd_id>`

数据会写入：

- `mvp/data/cloud_memory.db`
- 表：`nav_status`

可用 sqlite 查看：

```bash
sqlite3 mvp/data/cloud_memory.db 'select robot_id, cmd_id, status, ts from nav_status order by id;'
```

---

## 5. 运行测试

```bash
pytest mvp/tests -q
```

该测试使用 FakeBroker 做端到端模拟，不依赖真实 MQTT/ROS2。

---

## 6. ROS2 对接说明（下一步）

`mvp.robot.navigator.Ros2Navigator` 已预留对接点。

你接入真机时，可在 `move_chassis()` 内替换为：

- 发布 `geometry_msgs/Twist` 到 `/cmd_vel`，或
- 调用 Nav2 action（如 `NavigateToPose` / 自定义动作）

并将执行结果映射为状态上报。
