from __future__ import annotations

from ..adapters.base import RobotAdapter
from ..models import RunStatus
from ..run_store import RunRecord


def execute_get_position(record: RunRecord, adapter: RobotAdapter) -> None:
    pose = adapter.get_position()
    record.status = RunStatus.SUCCEEDED
    record.summary = "position fetched"
    record.data = {
        "frame_id": pose.frame_id,
        "x": pose.x,
        "y": pose.y,
        "yaw": pose.yaw,
    }
