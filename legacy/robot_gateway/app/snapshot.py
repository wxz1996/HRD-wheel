from __future__ import annotations

import cv2

from .webrtc.ros_source import FallbackFrameSource, ROS2_AVAILABLE, ROS2FrameSource


class SnapshotService:
    def __init__(self) -> None:
        self._fallback = FallbackFrameSource()
        self._ros_sources: dict[str, ROS2FrameSource] = {}

    def _get_source(self, camera_topic: str, width: int, height: int):
        if ROS2_AVAILABLE:
            key = f"{camera_topic}:{width}:{height}"
            if key not in self._ros_sources:
                source = ROS2FrameSource(camera_topic=camera_topic, width=width, height=height)
                source.start()
                self._ros_sources[key] = source
            return self._ros_sources[key]
        return self._fallback

    def get_jpeg(self, camera_topic: str, width: int, height: int) -> bytes:
        source = self._get_source(camera_topic, width, height)
        packet = source.get_latest_frame(camera_topic)
        if packet is None:
            raise TimeoutError(f"No frame from topic {camera_topic}")
        frame = cv2.resize(packet.frame, (width, height))
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            raise RuntimeError("Failed to encode JPEG")
        return bytes(buf)


snapshot_service = SnapshotService()
