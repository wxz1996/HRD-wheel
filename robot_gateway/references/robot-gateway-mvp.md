# Robot Gateway MVP Architecture (OpenClaw Data Plane)

## 目录

- [1. 文档目标](#1-文档目标)
- [2. 系统边界与职责](#2-系统边界与职责)
- [3. 部署拓扑](#3-部署拓扑)
- [4. 稳定任务协议（OpenClaw <-> Gateway）](#4-稳定任务协议openclaw---gateway)
- [5. 内部代码架构（Gateway 内部）](#5-内部代码架构gateway-内部)
- [6. 机器人通信契约（Gateway <-> Robot Agent）](#6-机器人通信契约gateway---robot-agent)
- [7. 典型时序](#7-典型时序)
- [8. 媒体能力（抓图/WebRTC）](#8-媒体能力抓图webrtc)
- [9. 运行与联调](#9-运行与联调)
- [10. 扩展指南](#10-扩展指南)
- [11. 已知限制与后续演进](#11-已知限制与后续演进)

## 1. 文档目标

这份文档用于回答三个关键问题：

1. OpenClaw 与 Robot Gateway 的边界是什么。
2. 协议和状态机哪些是“稳定契约”，不能随意改。
3. 第一次接手代码时，从哪里改、怎么验证不会破坏集成。

## 2. 系统边界与职责

### 2.1 控制面与数据面

- OpenClaw（控制面）
  - 任务编排
  - 策略决策
  - 会话与权限
  - 只依赖网关公开的稳定协议

- Robot Gateway（数据面，本仓库）
  - 技能执行（`get_status/get_position/move_to/capture_image`）
  - 任务状态机（`CREATED -> RUNNING -> SUCCEEDED|FAILED|CANCELED`）
  - 任务事件推送（WebSocket）
  - 媒体能力（抓图、WebRTC 信令）
  - 机器人通信适配（`mqtt_json`）

### 2.2 关键约束

- OpenClaw 不应直接依赖 ROS2 topic/action/service 细节。
- OpenClaw 不应依赖 Gateway 内部模块路径。
- Gateway 对控制面的稳定面应限定在 `v1` 协议和语义上。

## 3. 部署拓扑

### 3.1 推荐拓扑（解耦）

```text
OpenClaw (Control Plane)
        |
        | HTTP + WS (stable task protocol)
        v
robot-bridge (this project)
        |
        | MQTT JSON
        v
mqtt-broker (Mosquitto/EMQX)
        |
        v
robot-agent (runs in ROS2 environment)
        |
        v
ROS2 robot stack (topics/services/actions)
```

### 3.2 本仓库内角色

- `robot-bridge`：FastAPI 服务（`app/`）
- `../robot_agent`：独立机器人端 Agent 项目（建议用于真实 ROS2 集成）
- `mqtt-broker`：通过 `docker-compose.yml` 启动

## 4. 稳定任务协议（OpenClaw <-> Gateway）

> 这是控制面唯一应依赖的接口层。

### 4.1 能力发现

- `GET /v1/capabilities`
- 返回技能目录、权限要求、请求 schema

### 4.2 提交任务

- `POST /v1/tasks`
- 请求模型（`OpenClawTaskRequest`）：

```json
{
  "version": "1.0",
  "request_id": "req-001",
  "idempotency_key": "move-001",
  "session_id": "sess-001",
  "permissions": ["robot:move"],
  "skill": "move_to",
  "input": {
    "pose": {"frame_id": "map", "x": 8.0, "y": 3.0, "yaw": 0.5},
    "timeout_seconds": 10
  }
}
```

### 4.3 查询任务

- `GET /v1/tasks/{task_id}`

### 4.4 取消任务

- `POST /v1/tasks/{task_id}:cancel`

### 4.5 事件订阅

- `WS /v1/tasks/{task_id}/events`
- 事件模型：`RunEvent`
- `event` 类型：`progress | status_changed | artifact_created | log`

### 4.6 响应信封（Envelope）

关键字段语义：

- `version`: 当前固定 `1.0`
- `request_id`: 控制面请求关联 ID
- `idempotency_key`: 幂等键
- `run_id`: 数据面任务 ID（即 task_id）
- `status`: `CREATED|RUNNING|SUCCEEDED|FAILED|CANCELED`
- `ok`: 非 `FAILED` 时为 `true`
- `data/artifacts/telemetry/error`: 业务输出

### 4.7 协议语义约定

- 协议版本检查：`version != 1.0` 返回 `400`
- 权限校验：权限不满足返回 `403`
- 幂等语义：相同 `idempotency_key + skill` 重复提交返回同一 `run_id`
- 幂等冲突：相同 `idempotency_key` 但不同 skill 返回 `409`

### 4.8 旧接口清理状态

旧路径 `POST /skills/{skill}:run`、`GET /runs/{run_id}`、`POST /runs/{run_id}:cancel` 与 `WS /ws/runs/{run_id}` 已移除。
控制面调用统一收敛到 `/v1/tasks*` 与 `WS /v1/tasks/{task_id}/events`。

## 5. 内部代码架构（Gateway 内部）

### 5.1 主入口

- `app/main.py`
  - 路由定义
  - 请求校验、权限检查
  - skill 分发
  - 适配器实例化

### 5.2 协议模型

- `app/models.py`
  - `Envelope`、`RunEvent`、`OpenClawTaskRequest`
  - 各技能请求模型（`MoveToRequest` 等）

### 5.3 任务状态管理

- `app/run_store.py`
  - `RunRecord`
  - `RunStore`
  - 幂等索引
  - 取消信号（`cancel_event`）

### 5.4 技能执行层

- `app/skills/get_status.py`
- `app/skills/get_position.py`
- `app/skills/move_to.py`
- `app/skills/capture_image.py`

### 5.5 事件推送

- `app/ws_manager.py`

### 5.6 设备适配层

- `app/adapters/base.py`: 统一接口
- `app/adapters/factory.py`: 适配器工厂
- `app/adapters/mqtt_json_adapter.py`: 通过 MQTT 调机器人 Agent

## 6. 机器人通信契约（Gateway <-> Robot Agent）

Gateway 默认采用 `mqtt_json` 适配器，通过 MQTT JSON 调机器人 Agent（Agent 内部可接 ROS2）。

### 6.1 主题约定

- 命令主题：`{prefix}/robot/{robot_id}/cmd`
- 回复主题：`{prefix}/gateway/{gateway_client_id}/reply`

默认变量：

- `prefix=hrd`
- `robot_id=robot-001`

### 6.2 请求消息（Gateway -> Agent）

```json
{
  "protocol": "mqtt-json-v1",
  "timestamp": 1710000000,
  "correlation_id": "corr-abc123",
  "reply_to": "hrd/gateway/gateway-xxxx/reply",
  "action": "move_to",
  "payload": {
    "location": null,
    "pose": {"frame_id": "map", "x": 8.0, "y": 3.0, "yaw": 0.5},
    "timeout_seconds": 4
  }
}
```

### 6.3 响应消息（Agent -> Gateway）

```json
{
  "protocol": "mqtt-json-v1",
  "timestamp": 1710000001,
  "correlation_id": "corr-abc123",
  "ok": true,
  "data": {
    "accepted": true,
    "message": "ROS2 nav command accepted and completed",
    "final_pose": {"frame_id": "map", "x": 8.0, "y": 3.0, "yaw": 0.5},
    "ros2_meta": {
      "action_server": "/navigate_to_pose",
      "result_code": 0
    }
  }
}
```

### 6.4 Agent 侧 action 约定

- `get_status`
- `get_position`
- `move_to`
- `capture_image`
- 真实机器人端建议使用 [../robot_agent/README.md](../../robot_agent/README.md)

## 7. 典型时序

### 7.1 `get_status`

1. OpenClaw 调 `POST /v1/tasks`（`skill=get_status`）
2. Gateway 校验版本/权限，创建 run
3. 调 `adapter.get_status()`
4. 更新 `SUCCEEDED`，返回 `Envelope`

### 7.2 `move_to`

1. OpenClaw 调 `POST /v1/tasks`（`skill=move_to`）
2. Gateway 创建异步任务，状态从 `CREATED` 进入 `RUNNING`
3. 期间发布 progress 事件（WS）
4. 调 `adapter.move_to(...)`
5. 成功后 `SUCCEEDED`，返回最终位姿和 `ros2_meta`
6. 若收到取消请求，状态转 `CANCELED`

## 8. 媒体能力（抓图/WebRTC）

- 抓图：`GET /snapshot`
- WebRTC：`POST /webrtc/offer`、`POST /webrtc/{session_id}:close`、`GET /webrtc/sessions`

实现要点：

- 若 ROS2 图像依赖可用，尝试从 ROS2 topic 取帧
- 否则自动 fallback 到模拟帧源
- `capture_image` skill 会生成 JPEG artifact 并挂到 `/artifacts/*`

## 9. 运行与联调

### 9.1 本地启动

```bash
cd robot_gateway
docker compose up -d mqtt-broker
uv venv
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

### 9.2 单测

```bash
uv run pytest tests/test_api.py
```

### 9.3 虚拟 OpenClaw 全流程验证

```bash
uv run python scripts/test_openclaw_ros2_flow.py --base-url http://127.0.0.1:8000
```

### 9.4 MQTT 桥接验证（Gateway 无 ROS2）

```bash
# terminal A: robot agent（ROS2）
# 见 ../../robot_agent/README.md

# terminal B: gateway
export ROBOT_ADAPTER=mqtt_json
export MQTT_HOST=127.0.0.1
export MQTT_PORT=1883
export MQTT_TOPIC_PREFIX=hrd
export MQTT_ROBOT_ID=robot-001
uv run uvicorn app.main:app --reload --port 8000

# terminal C: virtual openclaw
uv run python scripts/test_openclaw_ros2_flow.py --base-url http://127.0.0.1:8000 --expected-adapter mqtt_json
```

### 9.5 Compose 一键联调

```bash
docker compose up --build
```

## 10. 扩展指南

### 10.1 新增 skill

1. 在 `app/models.py` 增加请求模型
2. 在 `app/skills/` 新增执行模块
3. 在 `app/main.py` 的 `SKILL_POLICIES` 和 `_start_skill` 注册
4. 在 `tests/test_api.py` 增加行为测试

### 10.2 新增机器人通信方式

1. 在 `app/adapters/` 新增实现类（实现 `RobotAdapter`）
2. 在 `app/adapters/factory.py` 注册 name
3. 在 `app/config.py` 增加配置项
4. 补充端到端验证脚本/测试

### 10.3 替换运行态存储

当前 `RunStore` 默认内存实现，可替换为 Redis/DB：

1. 实现 `RunPersistence`
2. 将 `run_store` 注入新持久化层
3. 保持幂等语义和状态机语义不变

## 11. 已知限制与后续演进

当前 MVP 的限制：

- `RunStore` 为内存态，进程重启后 run 丢失
- `move_to` 进度为模拟进度，不代表机器人真实轨迹进度
- WebRTC 当前走 fallback 帧源，尚未绑定 ROS2 实时视频 track

建议优先演进顺序：

1. 运行态持久化（RunStore + 幂等索引）
2. 真实 ROS2 Agent（action/service/topic）与 MQTT bridge 一致性
3. 统一 tracing/request_id 贯通 OpenClaw -> Gateway -> Robot Agent
4. 鉴权增强（broker ACL、topic 隔离、token 校验）
