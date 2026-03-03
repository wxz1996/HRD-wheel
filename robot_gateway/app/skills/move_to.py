from __future__ import annotations

import asyncio

from ..models import MoveToRequest, RunEvent, RunStatus
from ..run_store import RunRecord
from ..ws_manager import WSManager


async def execute_move_to(record: RunRecord, req: MoveToRequest, ws_manager: WSManager) -> None:
    record.status = RunStatus.RUNNING
    record.summary = "move_to started"
    await ws_manager.publish(
        RunEvent(run_id=record.run_id, event="status_changed", status=record.status, message=record.summary)
    )

    steps = 10
    sleep_s = max(0.2, req.timeout_seconds / steps / 3)
    for idx in range(steps):
        if record.cancel_event.is_set():
            record.status = RunStatus.CANCELED
            record.summary = "move_to canceled"
            await ws_manager.publish(
                RunEvent(run_id=record.run_id, event="status_changed", status=record.status, message=record.summary)
            )
            return
        percent = int((idx + 1) * 100 / steps)
        record.telemetry = {"percent": percent}
        await ws_manager.publish(
            RunEvent(
                run_id=record.run_id,
                event="progress",
                status=record.status,
                percent=percent,
                message=f"moving... {percent}%",
                telemetry=record.telemetry,
            )
        )
        await asyncio.sleep(sleep_s)

    if record.cancel_event.is_set():
        record.status = RunStatus.CANCELED
        record.summary = "move_to canceled"
    else:
        record.status = RunStatus.SUCCEEDED
        record.summary = "move_to completed"
        record.data = {
            "target": req.location or req.pose.model_dump() if req.pose else None,
            "timeout_seconds": req.timeout_seconds,
        }
    await ws_manager.publish(
        RunEvent(run_id=record.run_id, event="status_changed", status=record.status, message=record.summary)
    )
