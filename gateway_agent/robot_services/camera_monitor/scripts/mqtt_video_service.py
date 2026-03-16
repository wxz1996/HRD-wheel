import base64
import json
import threading
import time
from dataclasses import dataclass
from typing import Optional

from robot_services.common import MqttService

"""MQTT 视频接入服务。

本模块是机器人视频通道：
robot 发布 JPEG 到 MQTT -> gateway 订阅并缓存最新帧；
API 层再从该内存帧缓存输出状态与 MJPEG 视频流。
"""


@dataclass
class VideoStatus:
    connected: bool
    topic: str
    frame_seq: int
    last_frame_ts: float
    source: str


class FrameHub:
    """视频接口共享的内存最新帧缓存。"""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._frame: Optional[bytes] = None
        self._seq = 0
        self._last_ts = 0.0
        self._source = "none"

    def publish(self, frame: bytes, source: str) -> None:
        with self._cond:
            self._frame = frame
            self._seq += 1
            self._last_ts = time.time()
            self._source = source
            self._cond.notify_all()

    def wait_for_frame(self, last_seq: int, timeout_s: float = 1.0) -> tuple[int, Optional[bytes], float]:
        with self._cond:
            if self._seq <= last_seq:
                self._cond.wait(timeout_s)
            return self._seq, self._frame, self._last_ts

    def snapshot(self) -> tuple[int, Optional[bytes], float, str]:
        with self._cond:
            return self._seq, self._frame, self._last_ts, self._source


class MqttVideoService(MqttService):
    """订阅 MQTT 机器人视频 topic，并写入 FrameHub。"""

    def __init__(self) -> None:
        super().__init__(
            default_client_id="hrt-gateway-video",
            topic_env_var="HRT_MQTT_VIDEO_TOPIC",
            default_topic="hrt/camera/color/jpeg",
        )
        self.frames = FrameHub()

    def status(self) -> VideoStatus:
        seq, _, ts, source = self.frames.snapshot()
        return VideoStatus(
            connected=self.connected,
            topic=self.topic,
            frame_seq=seq,
            last_frame_ts=ts,
            source=source,
        )

    def on_mqtt_message(self, topic: str, payload: bytes) -> None:
        del topic
        # Preferred format: raw JPEG binary payload
        if len(payload) > 2 and payload[0] == 0xFF and payload[1] == 0xD8:
            self.frames.publish(payload, source="mqtt:jpeg")
            return

        # Compatible format: {"jpeg_b64":"..."} or {"data":"data:image/jpeg;base64,..."}
        try:
            obj = json.loads(payload.decode("utf-8"))
            data = obj.get("jpeg_b64") or obj.get("data") or ""
            if data.startswith("data:image/jpeg;base64,"):
                data = data.split(",", 1)[1]
            if data:
                self.frames.publish(base64.b64decode(data), source="mqtt:json_b64")
        except Exception:
            return


_video_service_singleton: Optional[MqttVideoService] = None


def get_mqtt_video_service() -> MqttVideoService:
    """返回进程级单例 MQTT 视频服务。"""
    global _video_service_singleton
    if _video_service_singleton is None:
        _video_service_singleton = MqttVideoService()
    return _video_service_singleton
