from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from robot_services.common import MqttService


@dataclass
class VisionStatus:
    connected: bool
    command_topic: str
    status_topic: str
    active_task_id: str | None
    last_report: dict[str, Any] | None


class MqttVisionService(MqttService):
    """Minimal MQTT vision service wrapper for scene-monitor tasks."""

    def __init__(self) -> None:
        self.status_topic = os.getenv("HRT_MQTT_VISION_STATUS_TOPIC", "hrt/robot/vision/status")
        super().__init__(
            default_client_id="hrt-gateway-vision",
            topic_env_var="HRT_MQTT_VISION_STATUS_TOPIC",
            default_topic=self.status_topic,
        )
        self.command_topic = os.getenv("HRT_MQTT_VISION_CMD_TOPIC", "hrt/robot/vision/cmd")
        self._active_task_id: str | None = None
        self._last_report: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def status(self) -> VisionStatus:
        with self._lock:
            active_task_id = self._active_task_id
            last_report = self._last_report
        return VisionStatus(
            connected=self.connected,
            command_topic=self.command_topic,
            status_topic=self.status_topic,
            active_task_id=active_task_id,
            last_report=last_report,
        )

    def start_scene_monitor(
        self,
        *,
        task_id: str,
        scene: str,
        target_name: str,
        source: str = "gateway",
    ) -> None:
        payload = {
            "type": "vision_task_start",
            "taskId": task_id,
            "scene": scene,
            "targetName": target_name,
            "source": source,
            "ts": time.time(),
        }
        with self._lock:
            self._active_task_id = task_id
        self.publish(self.command_topic, json.dumps(payload), qos=0, retain=False)

    def stop_scene_monitor(self, *, task_id: str, source: str = "gateway") -> None:
        payload = {
            "type": "vision_task_stop",
            "taskId": task_id,
            "source": source,
            "ts": time.time(),
        }
        self.publish(self.command_topic, json.dumps(payload), qos=0, retain=False)

    def on_mqtt_message(self, topic: str, payload: bytes) -> None:
        if topic != self.status_topic:
            return
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except Exception:
            return
        if not isinstance(decoded, dict):
            return
        with self._lock:
            self._last_report = decoded
            self._active_task_id = decoded.get("taskId") or self._active_task_id


_vision_service_singleton: MqttVisionService | None = None


def get_mqtt_vision_service() -> MqttVisionService:
    """Return the process-wide MQTT vision service singleton."""
    global _vision_service_singleton
    if _vision_service_singleton is None:
        _vision_service_singleton = MqttVisionService()
    return _vision_service_singleton
