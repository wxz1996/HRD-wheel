# HRT v0.0.1 MVP Demo

本次交付聚焦最小闭环：

**Web 前端 -> FastAPI 网关 -> MQTT -> robot_agent -> ROS2 相机 topic**

## 目录结构

- `web_fronted/`: Next.js + TypeScript 前端（`/login`, `/home`, `/ar`）
- `gateway_agent/`: FastAPI 网关（REST + WebSocket + MQTT 视频桥接）
- `robot_agent/`: 机器人端 ROS2 视频桥接（RealSense topic -> MQTT）
- `docs/mvp-api.md`: MVP 接口文档

## 快速启动

### 0) Python 环境（uv）

```bash
# 在仓库根目录执行，一次性同步 workspace 下所有 Python 子项目
uv sync --all-packages
```

### 1) 启动网关（gateway_agent）

```bash
# 获取本机局域网 IP（用于手机同 Wi-Fi 访问）
IP=$(route get default 2>/dev/null | awk '/interface:/{print $2}' | xargs -I{} ipconfig getifaddr {})
echo "$IP"

export HRT_MQTT_HOST=127.0.0.1
export HRT_MQTT_PORT=1883
export HRT_MQTT_VIDEO_TOPIC=hrt/camera/color/jpeg
export HRT_ALLOWED_ORIGINS="http://$IP:3000,http://localhost:3000,http://127.0.0.1:3000"

uv run --project gateway_agent uvicorn main:app --app-dir gateway_agent --host 0.0.0.0 --port 8000 --reload
```

### 1.5) 启动 MQTT Broker

```bash
# macOS（若未部署）
brew install mosquitto

# 开发模式（允许局域网连接，无鉴权）
mosquitto -c gateway_agent/mosquitto/mosquitto.dev.conf

# 生产建议（开启用户名密码）
# 先创建账号：
#   mosquitto_passwd -c /opt/homebrew/etc/mosquitto/passwd hrt
# 再启动：
#   mosquitto -c gateway_agent/mosquitto/mosquitto.auth.conf

# 或 Linux
# sudo apt install mosquitto
# sudo systemctl start mosquitto
```

### 2) 启动机器人视频桥接（robot_agent，在机器人端）

```bash
# 可选：同步 robot_agent 的 Python 依赖（paho-mqtt 等）
uv sync --project robot_agent

# robot_agent 通过 ROS2/colcon 运行
colcon build --packages-select robot_agent
source install/setup.bash
ros2 launch robot_agent robot_agent.launch.py \
  mqtt_host:=<MQTT_BROKER_IP> \
  camera_topic:=/camera/color/image_raw \
  video_topic:=hrt/camera/color/jpeg \
  stream_fps:=30 \
  start_realsense:=true
```

说明：
- 默认订阅：`/camera/color/image_raw`
- 默认发布：`hrt/camera/color/jpeg`
- 若 broker 不在机器人本机，`mqtt_host` 不能填 `127.0.0.1`，应填 broker 机器的局域网 IP

### 2.1) Broker 自检（建议）

```bash
# 1) 确认 1883 监听（应看到 0.0.0.0:1883 或实际网卡地址）
lsof -nP -iTCP:1883 -sTCP:LISTEN

# 2) 确认视频 topic 有帧（如果超时，说明 robot_agent 没有推到 broker）
mosquitto_sub -h 127.0.0.1 -p 1883 -t hrt/camera/color/jpeg -C 1 -W 5 -N | wc -c

# 3) 网关视频状态
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/login \
  -H 'content-type: application/json' \
  -d '{"account":"demo","password":"demo123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl -s http://127.0.0.1:8000/api/video/status -H "Authorization: Bearer $TOKEN"
```

### 2.5) 多个 robot_agent 并存（同一 broker）

- 每个 agent 必须使用唯一 `robot_id`（避免 MQTT client_id 冲突）
- 每个 agent 必须使用唯一 `video_topic`（避免视频流混流）
- 当前网关一次只订阅一个 `HRT_MQTT_VIDEO_TOPIC`，切换机器人后需重启网关

### 3) 启动前端（web_fronted）

```bash
IP=$(route get default 2>/dev/null | awk '/interface:/{print $2}' | xargs -I{} ipconfig getifaddr {})
cd web_fronted
npm install
NEXT_PUBLIC_API_BASE="http://$IP:8000" npm run dev -- --hostname 0.0.0.0 --port 3000
```

访问：
- 本机：`http://localhost:3000/login` 或 `http://127.0.0.1:3000/login`
- 手机同 Wi-Fi：`http://<你的局域网IP>:3000/login`

## MVP 演示流程

1. `/login` 使用账号 `demo` / 密码 `demo123` 登录
2. 进入 `/home`，点击“进入 AR 控制”
3. 在 `/ar` 查看实时 RGB 视频、状态区、日志区
4. 拖动摇杆，网关 `/ws/control` 返回 ACK

## 安全默认值（v0.0.1）

- 登录默认账号：`demo`
- 登录默认密码：`demo123`
- 网关返回 Bearer Token，后续 REST / WS 需携带 token
- 可通过环境变量覆盖：
  - `HRT_DEMO_ACCOUNT`
  - `HRT_DEMO_PASSWORD`
  - `HRT_TOKEN_SECRET`
  - `HRT_STREAM_TOKEN_TTL_SECONDS`
  - `HRT_ALLOWED_ORIGINS`（逗号分隔）
  - `HRT_MQTT_HOST`
  - `HRT_MQTT_PORT`
  - `HRT_MQTT_VIDEO_TOPIC`

## 说明

- 当前不包含多机器人调度、云端鉴权与真实底盘控制闭环。
