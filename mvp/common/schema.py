"""Shared JSON schemas for cloud <-> robot messages."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Literal
from uuid import uuid4


CommandType = Literal["nav_action_goal"]
StatusType = Literal["accepted", "running", "success", "failed"]


def utc_millis() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


@dataclass
class CommandMessage:
    msg_id: str
    robot_id: str
    ts: int
    type: CommandType
    payload: Dict[str, Any]

    @staticmethod
    def new(
        robot_id: str,
        *,
        x: float,
        y: float = 0.0,
        z: float = 0.0,
        roll: float = 0.0,
        pitch: float = 0.0,
        yaw: float = 0.0,
        frame_id: str = "map",
    ) -> "CommandMessage":
        return CommandMessage(
            msg_id=str(uuid4()),
            robot_id=robot_id,
            ts=utc_millis(),
            type="nav_action_goal",
            payload={
                "action": "navigate_chassis",
                "goal": {
                    "frame_id": frame_id,
                    "x": x,
                    "y": y,
                    "z": z,
                    "roll": roll,
                    "pitch": pitch,
                    "yaw": yaw,
                },
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StatusMessage:
    msg_id: str
    robot_id: str
    ts: int
    cmd_id: str
    status: StatusType
    detail: Dict[str, Any]

    @staticmethod
    def new(
        *,
        robot_id: str,
        cmd_id: str,
        status: StatusType,
        detail: Dict[str, Any],
    ) -> "StatusMessage":
        return StatusMessage(
            msg_id=str(uuid4()),
            robot_id=robot_id,
            ts=utc_millis(),
            cmd_id=cmd_id,
            status=status,
            detail=detail,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
