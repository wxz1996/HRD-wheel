from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from robot_services.common import MqttService


@dataclass
class NavigationStatus:
    connected: bool
    command_topic: str
    status_topic: str
    active_goal_id: str | None
    last_report: dict[str, Any] | None


class MqttPointNavigationService(MqttService):
    """Minimal MQTT point-navigation service skeleton for future waypoint tasks."""

    def __init__(self) -> None:
        self.status_topic = os.getenv("HRT_MQTT_NAV_STATUS_TOPIC", "hrt/robot/navigation/status")
        super().__init__(
            default_client_id="hrt-gateway-point-navigation",
            topic_env_var="HRT_MQTT_NAV_STATUS_TOPIC",
            default_topic=self.status_topic,
        )
        self.command_topic = os.getenv("HRT_MQTT_NAV_CMD_TOPIC", "hrt/robot/navigation/cmd")
        self._active_goal_id: str | None = None
        self._last_report: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def status(self) -> NavigationStatus:
        with self._lock:
            active_goal_id = self._active_goal_id
            last_report = self._last_report
        return NavigationStatus(
            connected=self.connected,
            command_topic=self.command_topic,
            status_topic=self.status_topic,
            active_goal_id=active_goal_id,
            last_report=last_report,
        )

    def send_goal(
        self,
        *,
        goal_id: str,
        target_name: str,
        x: float | None = None,
        y: float | None = None,
        yaw: float | None = None,
        source: str = "gateway",
    ) -> None:
        payload = {
            "type": "navigate_to_point",
            "goalId": goal_id,
            "targetName": target_name,
            "pose": {
                "x": x,
                "y": y,
                "yaw": yaw,
            },
            "source": source,
            "ts": time.time(),
        }
        with self._lock:
            self._active_goal_id = goal_id
        self.publish(self.command_topic, json.dumps(payload), qos=0, retain=False)

    def cancel_goal(self, *, goal_id: str, source: str = "gateway") -> None:
        payload = {
            "type": "cancel_navigation",
            "goalId": goal_id,
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
            self._active_goal_id = decoded.get("goalId") or self._active_goal_id


_point_navigation_service_singleton: MqttPointNavigationService | None = None


def get_mqtt_point_navigation_service() -> MqttPointNavigationService:
    """Return the process-wide MQTT point-navigation service singleton."""
    global _point_navigation_service_singleton
    if _point_navigation_service_singleton is None:
        _point_navigation_service_singleton = MqttPointNavigationService()
    return _point_navigation_service_singleton
