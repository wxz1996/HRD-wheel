# Robot Gateway Codebase Map

## 这份文件解决什么问题

给第一次接手项目的人一个“从哪里开始看”和“改动应该落在哪”的地图，降低定位成本。

## 推荐阅读顺序

1. [app/main.py](../app/main.py)
2. [app/models.py](../app/models.py)
3. [app/run_store.py](../app/run_store.py)
4. [app/adapters/](../app/adapters)
5. [app/skills/](../app/skills)
6. [tests/test_api.py](../tests/test_api.py)

## 稳定面 vs 变化面

稳定面（改动要非常谨慎）：

- `/v1/capabilities`
- `/v1/tasks*`
- `Envelope` / `RunEvent` 字段语义
- 状态机：`CREATED -> RUNNING -> SUCCEEDED|FAILED|CANCELED`

变化面（可按需求演进）：

- skill 实现细节（`app/skills/*`）
- 机器人通信适配器（`app/adapters/*`）
- 媒体链路（`snapshot` / `webrtc`）

## 目录职责

### `app/main.py`

- API 路由入口
- 协议版本检查、权限检查
- skill 调度
- `/v1/tasks*` 与 WebSocket 事件入口

### `app/models.py`

- 协议模型定义
- `OpenClawTaskRequest`
- `Envelope`
- `RunEvent`

### `app/run_store.py`

- run 生命周期记录
- 幂等键映射
- 取消控制
- 持久化抽象接口（`RunPersistence`）

### `app/adapters/`

- `base.py`: 机器人通信抽象接口
- `factory.py`: 适配器选择入口
- `mqtt_json_adapter.py`: 经 MQTT 调机器人 Agent

### `app/skills/`

- `get_status.py`: 读状态
- `get_position.py`: 读位置
- `move_to.py`: 导航任务与进度事件
- `capture_image.py`: 抓图 artifact

### `app/ws_manager.py`

- run_id 级别事件订阅连接管理

### `app/snapshot.py` + `app/webrtc/`

- 抓图与 WebRTC 能力
- 与任务协议解耦，避免控制面耦合媒体细节

## 常见需求的改动入口

新增 skill：

1. `app/models.py` 增请求模型
2. `app/skills/` 新增执行文件
3. `app/main.py` 注册策略与分发
4. `tests/test_api.py` 增测试

新增通信协议：

1. `app/adapters/` 新实现
2. `app/adapters/factory.py` 注册
3. `app/config.py` 增配置
4. 增加脚本/测试验证

修改任务协议字段：

1. `app/models.py`
2. `app/main.py`
3. `tests/test_api.py`
4. `references/robot-gateway-mvp.md`

## 本地验证最小闭环

```bash
cd robot_gateway
uv sync --all-groups
uv run pytest tests/test_api.py
uv run python scripts/test_openclaw_ros2_flow.py --base-url http://127.0.0.1:8000
```
