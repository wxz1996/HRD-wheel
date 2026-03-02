"""Shared JSON schemas for cloud <-> robot messages."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from uuid import uuid4


CommandType = Literal["chassis_move"]
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
    def new(robot_id: str, vector: List[float]) -> "CommandMessage":
        return CommandMessage(
            msg_id=str(uuid4()),
            robot_id=robot_id,
            ts=utc_millis(),
            type="chassis_move",
            payload={"twist": vector},
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
