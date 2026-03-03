from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import numpy as np

try:
    import rclpy
    from cv_bridge import CvBridge
    from rclpy.node import Node
    from sensor_msgs.msg import Image as RosImage

    ROS2_AVAILABLE = True
except Exception:
    ROS2_AVAILABLE = False
    rclpy = None
    CvBridge = None
    Node = object
    RosImage = object


@dataclass
class FramePacket:
    frame: np.ndarray
    ts: float


class FallbackFrameSource:
    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.counter = 0

    def get_latest_frame(self, camera_topic: str | None = None) -> FramePacket:
        self.counter += 1
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        txt = f"fallback {self.counter} {time.strftime('%H:%M:%S')}"
        import cv2

        cv2.putText(img, txt, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)
        return FramePacket(frame=img, ts=time.time())


class ROS2FrameSource:
    def __init__(self, camera_topic: str, width: int = 640, height: int = 480) -> None:
        if not ROS2_AVAILABLE:
            raise RuntimeError("ROS2 is not available")
        self.camera_topic = camera_topic
        self.width = width
        self.height = height
        self._latest: FramePacket | None = None
        self._bridge = CvBridge()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False

        rclpy.init(args=None)
        self._node = rclpy.create_node("robot_gateway_frame_source")
        self._sub = self._node.create_subscription(RosImage, camera_topic, self._cb, 10)

    def _cb(self, msg: RosImage) -> None:
        import cv2

        cv = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        cv = cv2.resize(cv, (self.width, self.height))
        with self._lock:
            self._latest = FramePacket(frame=cv, ts=time.time())

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        def _spin() -> None:
            while self._running:
                rclpy.spin_once(self._node, timeout_sec=0.1)

        self._thread = threading.Thread(target=_spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._node.destroy_node()

    def get_latest_frame(self, camera_topic: str | None = None) -> FramePacket | None:
        with self._lock:
            return self._latest
