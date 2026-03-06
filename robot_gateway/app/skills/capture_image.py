from __future__ import annotations

from pathlib import Path

from ..adapters.base import RobotAdapter
from ..models import Artifact, CaptureImageRequest, ErrorInfo, RunStatus
from ..run_store import RunRecord, RunStore
from ..ws_manager import WSManager


def execute_capture_image(
    record: RunRecord,
    req: CaptureImageRequest,
    adapter: RobotAdapter,
    artifacts_dir: Path,
    base_url: str,
    store: RunStore,
) -> None:
    record.status = RunStatus.RUNNING
    record.summary = "capture_image started"
    store.update(record)

    img_path = artifacts_dir / "img" / f"{record.run_id}.jpg"
    img_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        capture = adapter.capture_image(camera=req.camera)
        img_path.write_bytes(capture.jpeg_bytes)
        url = f"{base_url}/artifacts/img/{record.run_id}.jpg"
        record.artifacts = [Artifact(type="image", mime=capture.mime, url=url, meta=capture.meta)]
        record.data = {"camera": req.camera, "source": "robot_agent"}
        record.status = RunStatus.SUCCEEDED
        record.summary = "capture_image completed"
    except Exception as exc:
        record.status = RunStatus.FAILED
        record.summary = "capture_image failed"
        record.error = ErrorInfo(code=502, message=str(exc), recovery_hint="check robot agent and camera")
    store.update(record)


async def publish_capture_events(record: RunRecord, ws_manager: WSManager) -> None:
    if record.status == RunStatus.SUCCEEDED:
        await ws_manager.publish(record.to_event(event="artifact_created", message="image created"))
    await ws_manager.publish(record.to_event(event="status_changed", message=record.summary))
