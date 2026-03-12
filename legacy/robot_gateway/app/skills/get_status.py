from __future__ import annotations

from ..adapters.base import RobotAdapter
from ..models import RunStatus
from ..run_store import RunRecord


def execute_get_status(record: RunRecord, adapter: RobotAdapter) -> None:
    status = adapter.get_status()
    record.status = RunStatus.SUCCEEDED
    record.summary = "status fetched"
    record.data = {"battery": status.battery, "mode": status.mode}
