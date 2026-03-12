from __future__ import annotations

import asyncio

from ..adapters.base import RobotAdapter, RobotPose
from ..models import MoveToRequest, RunStatus
from ..run_store import RunRecord, RunStore
from ..ws_manager import WSManager


async def execute_move_to(
    record: RunRecord,
    req: MoveToRequest,
    ws_manager: WSManager,
    store: RunStore,
    adapter: RobotAdapter,
) -> None:
    record.status = RunStatus.RUNNING
    record.summary = "move_to started"
    store.update(record)
    await ws_manager.publish(record.to_event(event="status_changed", message=record.summary))

    steps = 10
    sleep_s = max(0.2, req.timeout_seconds / steps / 3)
    for idx in range(steps):
        if record.cancel_event.is_set():
            record.status = RunStatus.CANCELED
            record.summary = "move_to canceled"
            store.update(record)
            await ws_manager.publish(record.to_event(event="status_changed", message=record.summary))
            return
        percent = int((idx + 1) * 100 / steps)
        record.telemetry = {"percent": percent}
        store.update(record)
        await ws_manager.publish(
            record.to_event(
                event="progress",
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
        target_pose = None
        if req.pose:
            target_pose = RobotPose(
                x=req.pose.x,
                y=req.pose.y,
                yaw=req.pose.yaw,
                frame_id=req.pose.frame_id or "map",
            )
        move_result = adapter.move_to(
            location=req.location,
            pose=target_pose,
            timeout_seconds=req.timeout_seconds,
        )
        record.status = RunStatus.SUCCEEDED
        record.summary = "move_to completed"
        record.data = {
            "target": req.location or req.pose.model_dump() if req.pose else None,
            "timeout_seconds": req.timeout_seconds,
            "adapter_result": {
                "accepted": move_result.accepted,
                "message": move_result.message,
                "final_pose": {
                    "frame_id": move_result.final_pose.frame_id,
                    "x": move_result.final_pose.x,
                    "y": move_result.final_pose.y,
                    "yaw": move_result.final_pose.yaw,
                },
                "ros2_meta": move_result.ros2_meta,
            },
        }
    store.update(record)
    await ws_manager.publish(record.to_event(event="status_changed", message=record.summary))
