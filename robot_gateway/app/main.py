from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from .adapters.factory import get_robot_adapter
from .config import settings
from .models import (
    CaptureImageRequest,
    Envelope,
    GetPositionRequest,
    GetStatusRequest,
    MoveToRequest,
    OpenClawTaskRequest,
    SkillCatalog,
    SkillDescriptor,
    WebRTCOfferRequest,
    WebRTCOfferResponse,
)
from .run_store import RunRecord, run_store
from .skills.capture_image import execute_capture_image, publish_capture_events
from .skills.get_position import execute_get_position
from .skills.get_status import execute_get_status
from .skills.move_to import execute_move_to
from .snapshot import snapshot_service
from .webrtc.manager import webrtc_manager
from .ws_manager import ws_manager

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
STATIC_DIR = ROOT / "static"

TASK_PROTOCOL_VERSION = "1.0"

SKILL_POLICIES: dict[str, dict[str, object]] = {
    "move_to": {
        "description": "Navigate robot to a named location or pose.",
        "cancellable": True,
        "idempotent": True,
        "required_permission": "robot:move",
        "schema": MoveToRequest.model_json_schema(),
    },
    "capture_image": {
        "description": "Capture one image from target camera and produce artifact URL.",
        "cancellable": False,
        "idempotent": True,
        "required_permission": "robot:camera",
        "schema": CaptureImageRequest.model_json_schema(),
    },
    "get_status": {
        "description": "Fetch current robot status from adapter.",
        "cancellable": False,
        "idempotent": True,
        "required_permission": "robot:status",
        "schema": GetStatusRequest.model_json_schema(),
    },
    "get_position": {
        "description": "Fetch robot pose from robot adapter.",
        "cancellable": False,
        "idempotent": True,
        "required_permission": "robot:position",
        "schema": GetPositionRequest.model_json_schema(),
    },
}

# 初始化服务
app = FastAPI(title="Robot Gateway MVP")
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts")
robot_adapter = get_robot_adapter(
    settings.robot_adapter,
    mqtt_host=settings.mqtt_host,
    mqtt_port=settings.mqtt_port,
    mqtt_topic_prefix=settings.mqtt_topic_prefix,
    mqtt_robot_id=settings.mqtt_robot_id,
    mqtt_timeout_seconds=settings.mqtt_timeout_seconds,
    mqtt_username=settings.mqtt_username,
    mqtt_password=settings.mqtt_password,
)


def _base_url() -> str:
    return f"http://localhost:{settings.robot_port}"


def _catalog() -> SkillCatalog:
    return SkillCatalog(
        version=TASK_PROTOCOL_VERSION,
        skills=[
            SkillDescriptor(
                name=name,
                description=str(meta["description"]),
                cancellable=bool(meta["cancellable"]),
                idempotent=bool(meta["idempotent"]),
                required_permission=str(meta["required_permission"]),
                request_schema=dict(meta["schema"]),
            )
            for name, meta in SKILL_POLICIES.items()
        ],
    )


def _check_protocol_version(version: str) -> None:
    if version != TASK_PROTOCOL_VERSION:
        raise HTTPException(status_code=400, detail=f"unsupported protocol version {version}")


def _authorize(skill_name: str, permissions: list[str] | None) -> None:
    if permissions is None:
        return
    required = str(SKILL_POLICIES[skill_name]["required_permission"])
    if required not in permissions:
        raise HTTPException(status_code=403, detail=f"permission denied for skill {skill_name}")


def _validate_skill_request(skill_name: str, payload: dict) -> object:
    if skill_name == "move_to":
        return MoveToRequest.model_validate(payload)
    if skill_name == "capture_image":
        return CaptureImageRequest.model_validate(payload)
    if skill_name == "get_status":
        return GetStatusRequest.model_validate(payload or {})
    if skill_name == "get_position":
        return GetPositionRequest.model_validate(payload or {})
    raise HTTPException(status_code=404, detail=f"Unknown skill {skill_name}")


async def _start_skill(
    *,
    skill_name: str,
    payload: dict,
    request_id: str | None,
    idempotency_key: str | None,
    permissions: list[str] | None,
    session_id: str | None,
) -> RunRecord:
    skill_name = skill_name.strip()
    if skill_name not in SKILL_POLICIES:
        raise HTTPException(status_code=404, detail=f"Unknown skill {skill_name}")

    _authorize(skill_name, permissions)
    req = _validate_skill_request(skill_name, payload)

    try:
        record, created = run_store.create(
            skill=skill_name,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not created:
        return record

    if session_id:
        record.telemetry["session_id"] = session_id

    if skill_name == "move_to":
        asyncio.create_task(execute_move_to(record, req, ws_manager, run_store, robot_adapter))
        run_store.update(record)
        return record

    if skill_name == "capture_image":
        execute_capture_image(record, req, robot_adapter, ARTIFACTS_DIR, _base_url(), run_store)
        await publish_capture_events(record, ws_manager)
        return record

    if skill_name == "get_status":
        execute_get_status(record, robot_adapter)
    else:
        execute_get_position(record, robot_adapter)
    run_store.update(record)
    await ws_manager.publish(record.to_event(event="status_changed", message=record.summary))
    return record


@app.get("/v1/capabilities", response_model=SkillCatalog)
async def capabilities():
    return _catalog()


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "robot-bridge", "adapter": settings.robot_adapter}


@app.get("/v1/diagnostics/robot-link")
async def robot_link_diagnostics():
    try:
        status = robot_adapter.get_status()
        pose = robot_adapter.get_position()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"robot link check failed: {exc}") from exc
    return {
        "ok": True,
        "adapter": settings.robot_adapter,
        "status": {"battery": status.battery, "mode": status.mode},
        "position": {"frame_id": pose.frame_id, "x": pose.x, "y": pose.y, "yaw": pose.yaw},
    }

# 用装饰器声明路由，FastAPI 会按路径+方法分发请求
@app.post("/v1/tasks", response_model=Envelope)
async def create_task(req: OpenClawTaskRequest):
    _check_protocol_version(req.version)
    record = await _start_skill(
        skill_name=req.skill,
        payload=req.input,
        request_id=req.request_id,
        idempotency_key=req.idempotency_key,
        permissions=req.permissions,
        session_id=req.session_id,
    )
    return record.to_envelope()


@app.get("/v1/tasks/{task_id}", response_model=Envelope)
async def get_task(task_id: str):
    record = run_store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="task not found")
    return record.to_envelope()


@app.post("/v1/tasks/{task_id}:cancel", response_model=Envelope)
async def cancel_task(task_id: str):
    record = run_store.cancel(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="task not found")
    await ws_manager.publish(record.to_event(event="status_changed", message=record.summary))
    return record.to_envelope()


async def _ws_run_events(run_id: str, ws: WebSocket):
    await ws_manager.connect(run_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, ws)


@app.websocket("/v1/tasks/{task_id}/events")
async def ws_task_events(task_id: str, ws: WebSocket):
    await _ws_run_events(task_id, ws)


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
