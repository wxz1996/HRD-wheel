# Robot Gateway

`robot_gateway` 是 OpenClaw 体系下的数据面网关实现。

- OpenClaw（控制面）负责：任务编排、策略、会话、权限
- Robot Gateway（数据面）负责：技能执行、任务状态机、视频/抓图、设备适配
- 两者通过稳定任务协议通信：`/v1/capabilities` 与 `/v1/tasks*`

## 你第一次接手时先看什么

1. [references/robot-gateway-mvp.md](references/robot-gateway-mvp.md)
2. [references/codebase-map.md](references/codebase-map.md)
3. [app/main.py](app/main.py)
4. [tests/test_api.py](tests/test_api.py)

## 快速开始（10 分钟，默认 MQTT JSON）

```bash
# 先确保 MQTT broker 在 1883 可用
docker compose up -d mqtt-broker

uv venv
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

访问：`http://127.0.0.1:8000/healthz`

## 架构拆分

推荐拆成两个可独立演进的部分：

- `robot-bridge`：FastAPI 网关（本项目 `app/`）
- `mqtt-broker`：MQTT 消息基础设施（Mosquitto/EMQX）

机器人侧在 ROS2 环境中运行独立 Agent。

```text
OpenClaw (Control Plane)
        |
        | HTTP/WS Task Protocol
        v
robot-bridge (this project)
        |
        | MQTT JSON
        v
mqtt-broker
        |
        v
robot-agent (ROS2 environment)
```

## 运行模式

### 模式 A：本地协议验证（默认 `mqtt_json`）

```bash
# 1) broker
docker compose up -d mqtt-broker

# 2) robot agent（ROS2）
# 见 ../robot_agent/README.md

# 3) gateway（默认即 mqtt_json，可不显式设置 ROBOT_ADAPTER）
uv run uvicorn app.main:app --reload --port 8000
uv run python scripts/test_openclaw_ros2_flow.py --base-url http://127.0.0.1:8000 --expected-adapter mqtt_json
```

### 模式 B：Gateway 无 ROS2，走 MQTT 桥接

```bash
# 1) broker + 机器人侧 agent（ROS2）
docker compose up -d mqtt-broker
# 机器人侧 agent 启动见 ../robot_agent/README.md

# 2) gateway
export ROBOT_ADAPTER=mqtt_json
export MQTT_HOST=127.0.0.1
export MQTT_PORT=1883
export MQTT_TOPIC_PREFIX=hrd
export MQTT_ROBOT_ID=robot-001
uv run uvicorn app.main:app --reload --port 8000

# 3) 虚拟 openclaw 测试
uv run python scripts/test_openclaw_ros2_flow.py --base-url http://127.0.0.1:8000 --expected-adapter mqtt_json
```

### 模式 C：Docker Compose 一键联调

```bash
docker compose up --build
```

推荐后台方式（便于继续在终端执行测试）：

```bash
docker compose up -d --build
```

## 已验证联调流程（2026-03-05）

以下流程已在本仓库验证通过，适合第一次跑通 `mqtt_json`：

```bash
# 1) 启动两服务（Broker + Bridge）
docker compose up -d --build mqtt-broker robot-bridge

# 2) 启动机器人侧 agent（ROS2）
# 见 ../robot_agent/README.md

# 3) 查看状态
docker compose ps

# 4) 查看关键日志（确认 bridge 已启动）
docker compose logs --tail=80 robot-bridge

# 5) 端到端回归（宿主机执行）
uv run python scripts/test_openclaw_ros2_flow.py \
  --base-url http://127.0.0.1:8000 \
  --expected-adapter mqtt_json

# 6) 收尾
docker compose down
```

预期成功标志：脚本末尾打印 `OpenClaw virtual flow PASSED`。

## 依赖与运行时说明（本次补充）

- 容器基础镜像：`python:3.11-slim`
- Python 工具：`uv`
- MQTT Python 库：`paho-mqtt`（使用 Callback API v2）
- Broker：`eclipse-mosquitto:2`
- OpenCV 运行时系统库（容器内）：
  - `libxcb1`
  - `libglib2.0-0`
  - `libgl1`
- 网关静态目录（容器内）：`/app/artifacts`（镜像构建时创建）

对应 Docker 构建定义见 `deploy/docker/Dockerfile.bridge`。

## 常见问题排查

1. `ConnectionRefusedError: [Errno 61]`（连接 `127.0.0.1:1883` 失败）

- 原因：MQTT Broker 未启动。
- 处理：

```bash
docker compose up -d mqtt-broker
```

2. `ImportError: libxcb.so.1: cannot open shared object file`

- 原因：容器缺 OpenCV 运行时依赖。
- 处理：已在镜像中安装 `libxcb1/libglib2.0-0/libgl1`；重新构建即可：

```bash
docker compose up -d --build robot-bridge
```

3. `RuntimeError: Directory '/app/artifacts' does not exist`

- 原因：网关启动时挂载静态目录，但容器内目录不存在。
- 处理：已在镜像构建阶段创建 `/app/artifacts`，重新构建后生效。

4. `TypeError` 与 `reason_code` 相关（Paho 回调）

- 原因：`reason_code` 在不同版本下可能是对象，不可直接 `int(reason_code)`。
- 处理：代码已统一做兼容转换并切到 Callback API v2。

## 对外 API（控制面唯一入口）

- `GET /v1/capabilities`
- `GET /v1/diagnostics/robot-link`
- `POST /v1/tasks`
- `GET /v1/tasks/{task_id}`
- `POST /v1/tasks/{task_id}:cancel`
- `WS /v1/tasks/{task_id}/events`

扩展能力：

- `GET /snapshot`
- `POST /webrtc/offer`
- `POST /webrtc/{session_id}:close`
- `GET /webrtc/sessions`
- `GET /debug/webrtc`

历史说明：

旧接口（`/skills/*`、`/runs/*`、`/ws/runs/*`）已移除，请统一使用 `/v1/tasks*` 与 `WS /v1/tasks/{task_id}/events`。

## 目录说明

- `app/`: 网关主代码
- `scripts/`: 联调脚本（虚拟 OpenClaw）
- `tests/`: API 行为测试
- `deploy/`: Docker 与 Broker 配置
- `references/`: 架构、协议、代码地图

## 常用开发命令

```bash
# 运行测试
uv run pytest tests/test_api.py

# OpenClaw 全链路回归
uv run python scripts/test_openclaw_ros2_flow.py --base-url http://127.0.0.1:8000
```

## 关键环境变量

- `ROBOT_ADAPTER`: `mqtt_json`（当前唯一支持值）
- `ROBOT_PORT`: HTTP 端口，默认 `8000`
- `MQTT_HOST` / `MQTT_PORT`
- `MQTT_TOPIC_PREFIX` / `MQTT_ROBOT_ID`
- `MQTT_TIMEOUT_SECONDS`
- `DEFAULT_CAMERA_TOPIC` / `DEFAULT_WIDTH` / `DEFAULT_HEIGHT` / `DEFAULT_FPS`
- `STUN_SERVER`（WebRTC 可选）

完整说明见 [references/robot-gateway-mvp.md](references/robot-gateway-mvp.md)。
