# HRT v0.0.1 MVP Demo

本次交付聚焦最小闭环：

**Web 前端 -> FastAPI 网关 -> 机器人接口声明（ROS2 风格）**

## 目录结构

- `frontend/`: Next.js + TypeScript 前端（`/login`, `/home`, `/ar`）
- `gateway/`: FastAPI 网关（REST + WebSocket + mock + adapter 骨架）
- `robot_interfaces/`: 机器人通信接口声明（messages/topics/services/adapters）
- `docs/mvp-api.md`: MVP 接口文档

## 快速启动

### 1) 启动网关（mock 模式）

```bash
cd gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2) 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：

- `http://localhost:3000/login`
- `http://localhost:3000/home`
- `http://localhost:3000/ar`

## MVP 演示流程

1. `/login` 输入非空账号密码进入 `/home`
2. `/home` 点击 “进入 AR 控制” 进入 `/ar`
3. `/ar` 查看 mock 视频、状态区、日志区
4. 打开识别开关，显示识别框
5. 点击识别框后高亮并向网关发送 selection
6. 拖动摇杆，网关 `/ws/control` 接收并返回 ACK

## 说明

- 当前不包含多机器人、真实鉴权、云端能力与真实机器人驱动。
- `gateway/robot_adapter/base_adapter.py` 与 `robot_interfaces/` 为后续真实接入预留。
