from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RobotStatus:
    battery: float
    mode: str


@dataclass
class RobotPose:
    x: float
    y: float
    yaw: float
    frame_id: str = "map"


@dataclass
class MoveCommandResult:
    accepted: bool
    message: str
    final_pose: RobotPose
    ros2_meta: dict[str, Any]


@dataclass
class CaptureImageResult:
    jpeg_bytes: bytes
    mime: str
    meta: dict[str, Any]


class RobotAdapter:
    def get_status(self) -> RobotStatus:
        raise NotImplementedError

    def get_position(self) -> RobotPose:
        raise NotImplementedError

    def move_to(
        self,
        *,
        location: str | None,
        pose: RobotPose | None,
        timeout_seconds: int,
    ) -> MoveCommandResult:
        raise NotImplementedError

    def capture_image(
        self,
        *,
        camera: str,
    ) -> CaptureImageResult:
        raise NotImplementedError
