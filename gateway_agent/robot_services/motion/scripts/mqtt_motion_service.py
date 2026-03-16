from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from robot_services.common import MqttService


@dataclass
class MotionAck:
    source: str
    ok: bool
    payload: dict[str, Any]
    received_at: float


@dataclass
class MotionStatus:
    connected: bool
    command_topic: str
    ack_topic: str
    last_ack: MotionAck | None


class MqttMotionService(MqttService):
    """Minimal MQTT motion service skeleton for future chassis control."""

    def __init__(self) -> None:
        self.ack_topic = os.getenv("HRT_MQTT_MOTION_ACK_TOPIC", "hrt/robot/motion/ack")
        super().__init__(
            default_client_id="hrt-gateway-motion",
            topic_env_var="HRT_MQTT_MOTION_ACK_TOPIC",
            default_topic=self.ack_topic,
        )
        self.command_topic = os.getenv("HRT_MQTT_MOTION_CMD_TOPIC", "hrt/robot/motion/cmd")
        self._last_ack: MotionAck | None = None
        self._ack_lock = threading.Lock()
        self._ack_cond = threading.Condition(self._ack_lock)

    def status(self) -> MotionStatus:
        with self._ack_lock:
            last_ack = self._last_ack
        return MotionStatus(
            connected=self.connected,
            command_topic=self.command_topic,
            ack_topic=self.ack_topic,
            last_ack=last_ack,
        )

    def wait_for_ack(self, after_ts: float, timeout_s: float = 0.2) -> MotionAck | None:
        deadline = time.time() + timeout_s
        with self._ack_cond:
            while True:
                ack = self._last_ack
                if ack is not None and ack.received_at >= after_ts:
                    return ack
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self._ack_cond.wait(remaining)

    def send_drive_command(
        self,
        *,
        x: float,
        y: float,
        source: str = "gateway",
    ) -> None:
        payload = {
            "type": "base_joystick",
            "payload": {
                "x": x,
                "y": y,
            },
            "source": source,
            "ts": time.time(),
        }
        self.publish(self.command_topic, json.dumps(payload), qos=0, retain=False)

    def on_mqtt_message(self, topic: str, payload: bytes) -> None:
        if topic != self.ack_topic:
            return
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except Exception:
            return
        ack = MotionAck(
            source=str(decoded.get("source", "robot")),
            ok=bool(decoded.get("ok", False)),
            payload=decoded if isinstance(decoded, dict) else {},
            received_at=time.time(),
        )
        with self._ack_cond:
            self._last_ack = ack
            self._ack_cond.notify_all()


_motion_service_singleton: MqttMotionService | None = None


def get_mqtt_motion_service() -> MqttMotionService:
    """Return the process-wide MQTT motion service singleton."""
    global _motion_service_singleton
    if _motion_service_singleton is None:
        _motion_service_singleton = MqttMotionService()
    return _motion_service_singleton
