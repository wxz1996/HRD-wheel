from __future__ import annotations

import asyncio
import fractions

import av

from .ros_source import FallbackFrameSource

try:
    from aiortc import VideoStreamTrack
except Exception:
    VideoStreamTrack = object  # type: ignore[assignment]


class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, source: FallbackFrameSource, camera_topic: str, fps: int = 15) -> None:
        super().__init__()
        self.source = source
        self.camera_topic = camera_topic
        self.fps = fps
        self._pts = 0

    async def recv(self) -> av.VideoFrame:
        await asyncio.sleep(1 / max(self.fps, 1))
        packet = self.source.get_latest_frame(self.camera_topic)
        frame = av.VideoFrame.from_ndarray(packet.frame, format="bgr24")
        self._pts += 1
        frame.pts = self._pts
        frame.time_base = fractions.Fraction(1, self.fps)
        return frame
