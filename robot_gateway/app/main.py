from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from .adapters.mock_adapter import mock_adapter
from .config import settings
from .models import (
    CaptureImageRequest,
    Envelope,
    GetStatusRequest,
    MoveToRequest,
    RunEvent,
    RunStatus,
    WebRTCOfferRequest,
    WebRTCOfferResponse,
)
from .run_store import run_store
from .skills.capture_image import execute_capture_image, publish_capture_events
from .skills.get_status import execute_get_status
from .skills.move_to import execute_move_to
from .snapshot import snapshot_service
from .webrtc.manager import webrtc_manager
from .ws_manager import ws_manager

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
STATIC_DIR = ROOT / "static"

app = FastAPI(title="Robot Gateway MVP")
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")


def _base_url() -> str:
    return f"http://localhost:{settings.robot_port}"


@app.post("/skills/{skill_name}:run", response_model=Envelope)
async def run_skill(skill_name: str, body: dict):
    skill_name = skill_name.strip()
    if skill_name == "move_to":
        req = MoveToRequest.model_validate(body)
        record = run_store.create(skill=skill_name)
        asyncio.create_task(execute_move_to(record, req, ws_manager))
        return record.to_envelope()

    if skill_name == "capture_image":
        req = CaptureImageRequest.model_validate(body)
        record = run_store.create(skill=skill_name)
        execute_capture_image(record, req, ARTIFACTS_DIR, _base_url())
        await publish_capture_events(record, ws_manager)
        return record.to_envelope()

    if skill_name == "get_status":
        _ = GetStatusRequest.model_validate(body or {})
        record = run_store.create(skill=skill_name)
        execute_get_status(record, mock_adapter)
        await ws_manager.publish(
            RunEvent(run_id=record.run_id, event="status_changed", status=record.status, message=record.summary)
        )
        return record.to_envelope()

    raise HTTPException(status_code=404, detail=f"Unknown skill {skill_name}")


@app.get("/runs/{run_id}", response_model=Envelope)
async def get_run(run_id: str):
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")
    return record.to_envelope()


@app.post("/runs/{run_id}:cancel", response_model=Envelope)
async def cancel_run(run_id: str):
    record = run_store.cancel(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")
    await ws_manager.publish(
        RunEvent(run_id=run_id, event="status_changed", status=record.status, message=record.summary)
    )
    return record.to_envelope()


@app.websocket("/ws/runs/{run_id}")
async def ws_runs(run_id: str, ws: WebSocket):
    await ws_manager.connect(run_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, ws)


@app.post("/webrtc/offer", response_model=WebRTCOfferResponse)
async def webrtc_offer(req: WebRTCOfferRequest):
    try:
        ans = await webrtc_manager.create_answer(
            sdp=req.sdp,
            typ=req.type,
            camera_topic=req.camera_topic or settings.default_camera_topic,
            width=req.width or settings.default_width,
            height=req.height or settings.default_height,
            fps=req.fps or settings.default_fps,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return WebRTCOfferResponse.model_validate(ans)


@app.post("/webrtc/{session_id}:close")
async def webrtc_close(session_id: str):
    ok = await webrtc_manager.close(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True, "session_id": session_id}


@app.get("/webrtc/sessions")
async def webrtc_sessions():
    return {"sessions": webrtc_manager.list_sessions()}


@app.get("/debug/webrtc")
async def debug_webrtc():
    return FileResponse(STATIC_DIR / "webrtc_debug.html")


@app.get("/snapshot")
async def snapshot(
    camera_topic: str = Query(default=settings.default_camera_topic),
    width: int = Query(default=settings.default_width),
    height: int = Query(default=settings.default_height),
):
    try:
        jpeg_bytes = snapshot_service.get_jpeg(camera_topic, width, height)
    except TimeoutError as exc:
        return PlainTextResponse(str(exc), status_code=503)
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await webrtc_manager.close_all()
