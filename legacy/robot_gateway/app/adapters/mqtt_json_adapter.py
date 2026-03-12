from __future__ import annotations

import base64
import json
import threading
import time
import uuid
from typing import Any

try:
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - optional runtime dependency
    mqtt = None  # type: ignore[assignment]

from .base import CaptureImageResult, MoveCommandResult, RobotAdapter, RobotPose, RobotStatus


def _reason_code_value(reason_code: Any) -> int:
    value = getattr(reason_code, "value", reason_code)
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


class MqttJsonRobotAdapter(RobotAdapter):
    """
    Bridge Gateway to robot-side agent via MQTT JSON request/response.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        topic_prefix: str,
        robot_id: str,
        timeout_seconds: float = 6.0,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required for ROBOT_ADAPTER=mqtt_json")
        self._timeout_seconds = timeout_seconds
        self._topic_prefix = topic_prefix.rstrip("/")
        self._robot_id = robot_id

        self._client_id = f"gateway-{uuid.uuid4().hex[:10]}"
        self._reply_topic = f"{self._topic_prefix}/gateway/{self._client_id}/reply"
        self._cmd_topic = f"{self._topic_prefix}/robot/{self._robot_id}/cmd"

        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._responses: dict[str, dict[str, Any]] = {}
        self._connected = threading.Event()

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._client_id,
            clean_session=True,
        )
        if username:
            self._client.username_pw_set(username=username, password=password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(host, port, keepalive=30)
        self._client.loop_start()
        if not self._connected.wait(timeout=3.0):
            raise TimeoutError("mqtt adapter connect timeout")

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        del userdata, flags, properties
        if _reason_code_value(reason_code) != 0:
            return
        client.subscribe(self._reply_topic, qos=1)
        self._connected.set()

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        correlation_id = payload.get("correlation_id")
        if not correlation_id:
            return
        with self._cv:
            self._responses[correlation_id] = payload
            self._cv.notify_all()

    def _request(self, *, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        correlation_id = f"corr-{uuid.uuid4().hex[:12]}"
        body = {
            "protocol": "mqtt-json-v1",
            "timestamp": int(time.time()),
            "correlation_id": correlation_id,
            "reply_to": self._reply_topic,
            "action": action,
            "payload": payload,
        }
        info = self._client.publish(self._cmd_topic, json.dumps(body, ensure_ascii=False), qos=1)
        info.wait_for_publish(timeout=2.0)

        deadline = time.time() + self._timeout_seconds
        with self._cv:
            while time.time() < deadline:
                resp = self._responses.pop(correlation_id, None)
                if resp is not None:
                    if not resp.get("ok", False):
                        raise RuntimeError(resp.get("error", "robot agent request failed"))
                    return resp
                self._cv.wait(timeout=0.2)

        raise TimeoutError(f"mqtt request timeout action={action}")

    def get_status(self) -> RobotStatus:
        resp = self._request(action="get_status", payload={})
        data = resp.get("data", {})
        return RobotStatus(
            battery=float(data.get("battery", 0.0)),
            mode=str(data.get("mode", "UNKNOWN")),
        )

    def get_position(self) -> RobotPose:
        resp = self._request(action="get_position", payload={})
        data = resp.get("data", {})
        return RobotPose(
            frame_id=str(data.get("frame_id", "map")),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            yaw=float(data.get("yaw", 0.0)),
        )

    def move_to(
        self,
        *,
        location: str | None,
        pose: RobotPose | None,
        timeout_seconds: int,
    ) -> MoveCommandResult:
        req_payload: dict[str, Any] = {
            "location": location,
            "timeout_seconds": timeout_seconds,
        }
        if pose:
            req_payload["pose"] = {
                "frame_id": pose.frame_id,
                "x": pose.x,
                "y": pose.y,
                "yaw": pose.yaw,
            }
        resp = self._request(action="move_to", payload=req_payload)
        data = resp.get("data", {})
        final_pose_raw = data.get("final_pose", {})
        return MoveCommandResult(
            accepted=bool(data.get("accepted", True)),
            message=str(data.get("message", "move_to completed")),
            final_pose=RobotPose(
                frame_id=str(final_pose_raw.get("frame_id", "map")),
                x=float(final_pose_raw.get("x", 0.0)),
                y=float(final_pose_raw.get("y", 0.0)),
                yaw=float(final_pose_raw.get("yaw", 0.0)),
            ),
            ros2_meta=data.get("ros2_meta", {}),
        )

    def capture_image(
        self,
        *,
        camera: str,
    ) -> CaptureImageResult:
        resp = self._request(action="capture_image", payload={"camera": camera})
        data = resp.get("data", {})
        raw_b64 = data.get("image_jpeg_base64")
        if not isinstance(raw_b64, str) or not raw_b64:
            raise RuntimeError("invalid capture_image response: missing image_jpeg_base64")
        try:
            jpeg_bytes = base64.b64decode(raw_b64)
        except Exception as exc:
            raise RuntimeError(f"invalid capture_image response: {exc}") from exc
        return CaptureImageResult(
            jpeg_bytes=jpeg_bytes,
            mime=str(data.get("mime", "image/jpeg")),
            meta={
                "camera": data.get("camera", camera),
                "width": data.get("width"),
                "height": data.get("height"),
            },
        )
