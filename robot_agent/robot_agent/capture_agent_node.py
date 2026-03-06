from __future__ import annotations

import base64
import json
import threading
import time
from typing import Any

import cv2
import paho.mqtt.client as mqtt
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


def _reason_code_value(reason_code: Any) -> int:
    value = getattr(reason_code, "value", reason_code)
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


class CaptureAgentNode(Node):
    def __init__(self) -> None:
        super().__init__("capture_agent")

        self.declare_parameter("mqtt_host", "127.0.0.1")
        self.declare_parameter("mqtt_port", 1883)
        self.declare_parameter("topic_prefix", "hrd")
        self.declare_parameter("robot_id", "robot-001")
        self.declare_parameter("mqtt_username", "")
        self.declare_parameter("mqtt_password", "")
        self.declare_parameter("camera_topic", "/camera/color/image_raw")
        self.declare_parameter("jpeg_quality", 90)

        self._mqtt_host = str(self.get_parameter("mqtt_host").value)
        self._mqtt_port = int(self.get_parameter("mqtt_port").value)
        self._topic_prefix = str(self.get_parameter("topic_prefix").value).rstrip("/")
        self._robot_id = str(self.get_parameter("robot_id").value)
        self._mqtt_username = str(self.get_parameter("mqtt_username").value or "")
        self._mqtt_password = str(self.get_parameter("mqtt_password").value or "")
        self._camera_topic = str(self.get_parameter("camera_topic").value)
        self._jpeg_quality = int(self.get_parameter("jpeg_quality").value)

        self._cmd_topic = f"{self._topic_prefix}/robot/{self._robot_id}/cmd"

        self._bridge = CvBridge()
        self._frame_lock = threading.Lock()
        self._frame_cv = threading.Condition(self._frame_lock)
        self._latest_frame: Any = None

        self._sub = self.create_subscription(Image, self._camera_topic, self._on_image, 10)

        self._mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"robot-capture-agent-{self._robot_id}",
            clean_session=True,
        )
        if self._mqtt_username:
            self._mqtt.username_pw_set(self._mqtt_username, self._mqtt_password or None)
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_message = self._on_mqtt_message

    def start(self) -> None:
        self._mqtt.connect(self._mqtt_host, self._mqtt_port, keepalive=30)
        self._mqtt.loop_start()
        self.get_logger().info(
            f"capture_agent started mqtt={self._mqtt_host}:{self._mqtt_port} "
            f"topic_prefix={self._topic_prefix} robot_id={self._robot_id} "
            f"camera_topic={self._camera_topic}"
        )

    def stop(self) -> None:
        self._mqtt.loop_stop()
        self._mqtt.disconnect()

    def _on_image(self, msg: Image) -> None:
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warning(f"cv_bridge convert failed: {exc}")
            return
        with self._frame_cv:
            self._latest_frame = frame
            self._frame_cv.notify_all()

    def _on_mqtt_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        del userdata, flags, properties
        if _reason_code_value(reason_code) != 0:
            self.get_logger().error(f"mqtt connect failed reason_code={reason_code}")
            return
        client.subscribe(self._cmd_topic, qos=1)
        self.get_logger().info(f"subscribed: {self._cmd_topic}")

    def _on_mqtt_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        del userdata
        try:
            req = json.loads(msg.payload.decode("utf-8"))
        except Exception as exc:
            self.get_logger().warning(f"invalid json: {exc}")
            return

        correlation_id = str(req.get("correlation_id", ""))
        reply_to = str(req.get("reply_to", ""))
        action = str(req.get("action", ""))
        payload = req.get("payload", {}) or {}
        if not correlation_id or not reply_to:
            self.get_logger().warning("missing correlation_id or reply_to")
            return

        if action != "capture_image":
            body = self._build_err(correlation_id, f"unsupported action {action}")
        else:
            camera_name = str(payload.get("camera", "front"))
            try:
                jpeg, width, height = self._capture_latest_jpeg(timeout_seconds=3.0)
                body = self._build_ok(
                    correlation_id,
                    {
                        "camera": camera_name,
                        "mime": "image/jpeg",
                        "width": width,
                        "height": height,
                        "image_jpeg_base64": base64.b64encode(jpeg).decode("ascii"),
                    },
                )
            except Exception as exc:
                body = self._build_err(correlation_id, f"capture failed: {exc}")

        client.publish(reply_to, json.dumps(body, ensure_ascii=False), qos=1)
        self.get_logger().info(f"action={action} correlation_id={correlation_id} reply_to={reply_to}")

    def _capture_latest_jpeg(self, *, timeout_seconds: float) -> tuple[bytes, int, int]:
        deadline = time.time() + timeout_seconds
        with self._frame_cv:
            while self._latest_frame is None and time.time() < deadline:
                self._frame_cv.wait(timeout=0.1)
            if self._latest_frame is None:
                raise TimeoutError(f"no image frame from topic {self._camera_topic}")
            frame = self._latest_frame

        quality = max(1, min(100, self._jpeg_quality))
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            raise RuntimeError("failed to encode JPEG")
        height, width = frame.shape[:2]
        return bytes(buf), int(width), int(height)

    @staticmethod
    def _build_ok(correlation_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocol": "mqtt-json-v1",
            "timestamp": int(time.time()),
            "correlation_id": correlation_id,
            "ok": True,
            "data": data,
        }

    @staticmethod
    def _build_err(correlation_id: str, error: str) -> dict[str, Any]:
        return {
            "protocol": "mqtt-json-v1",
            "timestamp": int(time.time()),
            "correlation_id": correlation_id,
            "ok": False,
            "error": error,
        }


def main() -> int:
    rclpy.init(args=None)
    node = CaptureAgentNode()
    try:
        node.start()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0

