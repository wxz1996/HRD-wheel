from __future__ import annotations

import uuid
from dataclasses import dataclass

from ..config import settings
from .ros_source import FallbackFrameSource
from .tracks import CameraVideoTrack

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription
    from aiortc.rtcconfiguration import RTCConfiguration, RTCIceServer

    AIORTC_AVAILABLE = True
except Exception:
    RTCPeerConnection = None
    RTCSessionDescription = None
    RTCConfiguration = None
    RTCIceServer = None
    AIORTC_AVAILABLE = False


@dataclass
class SessionEntry:
    session_id: str
    pc: RTCPeerConnection
    camera_topic: str
    width: int
    height: int
    fps: int


class WebRTCManager:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionEntry] = {}

    def _make_config(self):
        if not settings.stun_server:
            return None
        if not AIORTC_AVAILABLE:
            return None
        return RTCConfiguration(iceServers=[RTCIceServer(urls=[settings.stun_server])])

    async def create_answer(
        self,
        sdp: str,
        typ: str,
        camera_topic: str,
        width: int,
        height: int,
        fps: int,
    ) -> dict:
        if not AIORTC_AVAILABLE:
            raise RuntimeError("aiortc is not installed")

        session_id = str(uuid.uuid4())
        pc = RTCPeerConnection(self._make_config())
        source = FallbackFrameSource(width=width, height=height)
        track = CameraVideoTrack(source=source, camera_topic=camera_topic, fps=fps)
        pc.addTrack(track)

        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=typ))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        self.sessions[session_id] = SessionEntry(
            session_id=session_id,
            pc=pc,
            camera_topic=camera_topic,
            width=width,
            height=height,
            fps=fps,
        )
        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "session_id": session_id,
        }

    async def close(self, session_id: str) -> bool:
        entry = self.sessions.pop(session_id, None)
        if not entry:
            return False
        await entry.pc.close()
        return True

    async def close_all(self) -> None:
        for session_id in list(self.sessions.keys()):
            await self.close(session_id)

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "camera_topic": s.camera_topic,
                "width": s.width,
                "height": s.height,
                "fps": s.fps,
            }
            for s in self.sessions.values()
        ]


webrtc_manager = WebRTCManager()
