---
name: robot-gateway
description: Build, run, debug, and extend the Robot Gateway FastAPI data-plane service used by OpenClaw control-plane. The gateway exposes stable task protocol endpoints (/v1/capabilities, /v1/tasks*) for orchestration, permission-aware skill execution, run lifecycle, snapshot JPEG capture, and WebRTC streaming. Use when handling requests about task protocol compatibility, skill handlers, run status flow, adapter integration, and runtime troubleshooting.
---

# Robot Gateway

Follow this workflow when working on this project.

## 1. Understand Scope

- Read `references/robot-gateway-mvp.md` for architecture, APIs, and runtime behavior.
- Inspect only relevant modules before editing:
  - `app/main.py` for routes and orchestration
  - `app/skills/` for skill behavior
  - `app/run_store.py` and `app/ws_manager.py` for run lifecycle and WebSocket events
  - `app/snapshot.py` and `app/webrtc/` for image/video streaming
  - `tests/test_api.py` for expected API behavior

## 2. Implement Changes

- Keep API envelope and status semantics consistent with existing models in `app/models.py`.
- Keep OpenClaw-facing protocol compatibility for `/v1/capabilities` and `/v1/tasks*`.
- Preserve run state machine: `CREATED -> RUNNING -> SUCCEEDED|FAILED|CANCELED`.
- Maintain cancellation safety for long-running skill tasks.
- Keep fallback behavior functional when ROS2 dependencies are unavailable.

## 3. Validate

- Ensure dependencies are synced before running checks:
  - `cd robot_gateway && uv sync --all-groups`
- Run targeted tests first, then full test file when possible:
  - `cd robot_gateway && uv run pytest tests/test_api.py`
- If changing dependencies or runtime configuration, verify startup command still works:
  - `cd robot_gateway && uv run uvicorn app.main:app --reload --port 8000`

## 4. Deliver

- Summarize changed API behavior explicitly.
- Note any compatibility impacts for OpenClaw control-plane integration.
- List unverified paths if environment limits prevent full validation.
