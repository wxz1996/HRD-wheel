from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from robot_services.common import MqttService


@dataclass
class ManipulationStatus:
    connected: bool
    command_topic: str
    status_topic: str
    active_task_id: str | None
    last_report: dict[str, Any] | None


class MqttManipulationService(MqttService):
    """Minimal MQTT manipulation service wrapper for future robot actions."""

    def __init__(self) -> None:
        self.status_topic = os.getenv("HRT_MQTT_MANIPULATION_STATUS_TOPIC", "hrt/robot/manipulation/status")
        super().__init__(
            default_client_id="hrt-gateway-manipulation",
            topic_env_var="HRT_MQTT_MANIPULATION_STATUS_TOPIC",
            default_topic=self.status_topic,
        )
        self.command_topic = os.getenv("HRT_MQTT_MANIPULATION_CMD_TOPIC", "hrt/robot/manipulation/cmd")
        self._active_task_id: str | None = None
        self._last_report: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def status(self) -> ManipulationStatus:
        with self._lock:
            active_task_id = self._active_task_id
            last_report = self._last_report
        return ManipulationStatus(
            connected=self.connected,
            command_topic=self.command_topic,
            status_topic=self.status_topic,
            active_task_id=active_task_id,
            last_report=last_report,
        )

    def execute_action(
        self,
        *,
        task_id: str,
        action_name: str,
        target_name: str,
        source: str = "gateway",
    ) -> None:
        payload = {
            "type": "manipulation_action",
            "taskId": task_id,
            "actionName": action_name,
            "targetName": target_name,
            "source": source,
            "ts": time.time(),
        }
        with self._lock:
            self._active_task_id = task_id
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


_manipulation_service_singleton: MqttManipulationService | None = None


def get_mqtt_manipulation_service() -> MqttManipulationService:
    """Return the process-wide MQTT manipulation service singleton."""
    global _manipulation_service_singleton
    if _manipulation_service_singleton is None:
        _manipulation_service_singleton = MqttManipulationService()
    return _manipulation_service_singleton
