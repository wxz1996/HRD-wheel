from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    robot_port: int = int(os.getenv("ROBOT_PORT", "8000"))
    robot_adapter: str = os.getenv("ROBOT_ADAPTER", "mqtt_json")
    mqtt_host: str = os.getenv("MQTT_HOST", "127.0.0.1")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic_prefix: str = os.getenv("MQTT_TOPIC_PREFIX", "hrd")
    mqtt_robot_id: str = os.getenv("MQTT_ROBOT_ID", "robot-001")
    mqtt_timeout_seconds: float = float(os.getenv("MQTT_TIMEOUT_SECONDS", "6.0"))
    mqtt_username: str | None = os.getenv("MQTT_USERNAME")
    mqtt_password: str | None = os.getenv("MQTT_PASSWORD")
    default_camera_topic: str = os.getenv("DEFAULT_CAMERA_TOPIC", "/camera/image_raw")
    default_width: int = int(os.getenv("DEFAULT_WIDTH", "640"))
    default_height: int = int(os.getenv("DEFAULT_HEIGHT", "480"))
    default_fps: int = int(os.getenv("DEFAULT_FPS", "15"))
    stun_server: str | None = os.getenv("STUN_SERVER")


settings = Settings()
