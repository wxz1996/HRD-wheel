from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from ..models import Artifact, CaptureImageRequest, RunEvent, RunStatus
from ..run_store import RunRecord
from ..ws_manager import WSManager


def execute_capture_image(
    record: RunRecord,
    req: CaptureImageRequest,
    artifacts_dir: Path,
    base_url: str,
) -> None:
    record.status = RunStatus.RUNNING
    record.summary = "capture_image started"

    img_path = artifacts_dir / "img" / f"{record.run_id}.jpg"
    img_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (640, 480), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    now = datetime.now().isoformat(timespec="seconds")
    draw.text((20, 20), f"camera={req.camera}", fill=(255, 255, 255))
    draw.text((20, 55), f"run_id={record.run_id}", fill=(200, 255, 200))
    draw.text((20, 90), now, fill=(200, 200, 255))
    image.save(img_path, format="JPEG")

    url = f"{base_url}/artifacts/img/{record.run_id}.jpg"
    record.artifacts = [Artifact(type="image", mime="image/jpeg", url=url)]
    record.data = {"camera": req.camera}
    record.status = RunStatus.SUCCEEDED
    record.summary = "capture_image completed"


async def publish_capture_events(record: RunRecord, ws_manager: WSManager) -> None:
    await ws_manager.publish(
        RunEvent(run_id=record.run_id, event="artifact_created", status=record.status, message="image created")
    )
    await ws_manager.publish(
        RunEvent(run_id=record.run_id, event="status_changed", status=record.status, message=record.summary)
    )
