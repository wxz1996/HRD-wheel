from __future__ import annotations

from .base import RobotAdapter
from .mqtt_json_adapter import MqttJsonRobotAdapter


def get_robot_adapter(
    name: str,
    *,
    mqtt_host: str = "127.0.0.1",
    mqtt_port: int = 1883,
    mqtt_topic_prefix: str = "hrd",
    mqtt_robot_id: str = "robot-001",
    mqtt_timeout_seconds: float = 6.0,
    mqtt_username: str | None = None,
    mqtt_password: str | None = None,
) -> RobotAdapter:
    normalized = (name or "").strip().lower()
    if normalized == "mqtt_json":
        return MqttJsonRobotAdapter(
            host=mqtt_host,
            port=mqtt_port,
            topic_prefix=mqtt_topic_prefix,
            robot_id=mqtt_robot_id,
            timeout_seconds=mqtt_timeout_seconds,
            username=mqtt_username,
            password=mqtt_password,
        )
    raise ValueError(
        f"unknown robot adapter '{name}', only 'mqtt_json' is supported"
    )
