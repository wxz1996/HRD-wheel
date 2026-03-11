# robot_agent (ROS2)

`robot_agent` 是 ROS2 Python 包，同时具备：

- 订阅 RealSense 图像 topic（默认 `/camera/color/image_raw`）
- 通过 MQTT JSON 与 `robot_gateway` 通信
- 处理 action：`capture_image` / `get_status` / `get_position` / `move_to`

## 包结构

```text
robot_agent/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/robot_agent
├── launch/robot_agent.launch.py
├── robot_agent/
│   ├── __init__.py
│   └── capture_agent_node.py
└── scripts/
    └── run_robot_agent.py
```

## 依赖（ROS2 环境）

- `rclpy`
- `sensor_msgs`
- `cv_bridge`
- `python3-opencv`
- `python3-paho-mqtt`
- RealSense 驱动节点（例如 `realsense2_camera`）发布图像 topic

## 构建

在 ROS2 工作区（例如 `~/ros2_ws/src`）放入本包后：

```bash
cd ~/ros2_ws
colcon build --packages-select robot_agent
source install/setup.bash
```

## 运行

先启动 RealSense ROS2 驱动（示例）：

```bash
ros2 launch realsense2_camera rs_launch.py
```

确认有图像 topic（默认）：

```bash
ros2 topic echo /camera/color/image_raw --once
```

方式 1：直接 run

```bash
ros2 run robot_agent capture_agent \
  --ros-args \
  -p mqtt_host:=192.168.0.114 \
  -p mqtt_port:=1883 \
  -p topic_prefix:=hrd \
  -p robot_id:=robot-001 \
  -p camera_topic:=/camera/color/image_raw \
  -p jpeg_quality:=90
```

方式 2：launch

```bash
ros2 launch robot_agent robot_agent.launch.py \
  mqtt_host:=192.168.0.114 \
  mqtt_port:=1883 \
  topic_prefix:=hrd \
  robot_id:=robot-001 \
  camera_topic:=/camera/color/image_raw \
  jpeg_quality:=90
```

## 与 Gateway 对齐

`robot_gateway` 侧需使用同一组 MQTT 参数：

- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_TOPIC_PREFIX`
- `MQTT_ROBOT_ID`

Gateway 会发 MQTT action 到：

- `{topic_prefix}/robot/{robot_id}/cmd`

Agent 按请求中的 `reply_to` 回包，数据字段包含：

- `mime`
- `width`
- `height`
- `image_jpeg_base64`
- `battery`
- `mode`
- `frame_id` / `x` / `y` / `yaw`
- `accepted` / `final_pose`

## Action 示例

### 1) `get_status`

请求：

```json
{
  "correlation_id": "c-001",
  "reply_to": "hrd/gateway/reply",
  "action": "get_status",
  "payload": {}
}
```

响应 `data` 主要字段：

- `battery`
- `mode`（默认 `AUTO`）
- `robot_id`
- `state`（默认 `idle`）
- `position`
- `last_action`
- `last_error`

### 2) `get_position`

请求：

```json
{
  "correlation_id": "c-002",
  "reply_to": "hrd/gateway/reply",
  "action": "get_position",
  "payload": {}
}
```

响应 `data` 主要字段：

- `position`（包含 `frame_id/x/y/z/yaw`）
- `frame_id`
- `x` / `y` / `z` / `yaw`

### 3) `move_to`

请求（兼容 `payload.pose` / `payload.target` / `payload.position`）：

```json
{
  "correlation_id": "c-003",
  "reply_to": "hrd/gateway/reply",
  "action": "move_to",
  "payload": {
    "pose": {
      "frame_id": "map",
      "x": 1.0,
      "y": 2.0,
      "yaw": 0.5
    }
  }
}
```

响应 `data` 主要字段：

- `accepted`
- `message`
- `final_pose`（包含 `frame_id/x/y/yaw`）
- `ros2_meta`
