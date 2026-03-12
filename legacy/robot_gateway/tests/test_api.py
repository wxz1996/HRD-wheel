from __future__ import annotations

import os
import time

from fastapi.testclient import TestClient

os.environ.setdefault("ROBOT_ADAPTER", "ros2_stub")

from app.main import app


client = TestClient(app)


def wait_until_done(run_id: str, timeout: float = 8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/v1/tasks/{run_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return resp.json()
        time.sleep(0.2)
    raise AssertionError("run did not finish in time")


def test_move_to_succeeds():
    resp = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-move-basic",
            "session_id": "sess-basic",
            "permissions": ["robot:move"],
            "skill": "move_to",
            "input": {"location": "dock", "timeout_seconds": 3},
        },
    )
    assert resp.status_code == 200
    created = resp.json()
    assert created["version"] == "1.0"
    assert created["request_id"]
    run_id = created["run_id"]

    final = wait_until_done(run_id)
    assert final["status"] == "SUCCEEDED"


def test_cancel_move_to():
    resp = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-move-cancel",
            "session_id": "sess-cancel",
            "permissions": ["robot:move"],
            "skill": "move_to",
            "input": {"location": "station", "timeout_seconds": 20},
        },
    )
    run_id = resp.json()["run_id"]

    time.sleep(0.5)
    cancel = client.post(f"/v1/tasks/{run_id}:cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELED"


def test_capture_image_artifact_accessible():
    resp = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-capture-1",
            "session_id": "sess-cap",
            "permissions": ["robot:camera"],
            "skill": "capture_image",
            "input": {"camera": "front"},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "SUCCEEDED"
    url = body["artifacts"][0]["url"]
    path = url.replace("http://localhost:8000", "")

    got = client.get(path)
    assert got.status_code == 200
    assert got.headers["content-type"].startswith("image/jpeg")


def test_snapshot_returns_jpeg():
    resp = client.get("/snapshot", params={"camera_topic": "/camera/image_raw", "width": 640, "height": 480})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/jpeg")
    assert len(resp.content) > 100


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["service"] == "robot-bridge"


def test_robot_link_diagnostics():
    resp = client.get("/v1/diagnostics/robot-link")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "adapter" in body
    assert "status" in body and "battery" in body["status"]
    assert "position" in body and "x" in body["position"]


def test_capabilities_and_openclaw_task():
    caps = client.get("/v1/capabilities")
    assert caps.status_code == 200
    body = caps.json()
    assert body["version"] == "1.0"
    assert {s["name"] for s in body["skills"]} >= {"move_to", "capture_image", "get_status", "get_position"}

    status_task = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-status-1",
            "session_id": "sess-001",
            "permissions": ["robot:status"],
            "skill": "get_status",
            "input": {},
        },
    )
    assert status_task.status_code == 200
    created = status_task.json()
    assert created["skill"] == "get_status"
    assert created["request_id"] == "req-status-1"
    assert created["status"] == "SUCCEEDED"
    assert created["data"]["mode"] in {"AUTO", "idle"}

    got = client.get(f"/v1/tasks/{created['run_id']}")
    assert got.status_code == 200
    assert got.json()["run_id"] == created["run_id"]

    move_task = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-move-1",
            "session_id": "sess-001",
            "permissions": ["robot:move"],
            "skill": "move_to",
            "input": {
                "pose": {"frame_id": "map", "x": 8.0, "y": 3.0, "yaw": 0.5},
                "timeout_seconds": 3,
            },
        },
    )
    assert move_task.status_code == 200
    move_run_id = move_task.json()["run_id"]
    move_final = wait_until_done(move_run_id)
    assert move_final["status"] == "SUCCEEDED"
    assert move_final["data"]["adapter_result"]["accepted"] is True
    assert move_final["data"]["adapter_result"]["final_pose"]["x"] == 8.0
    assert move_final["data"]["adapter_result"]["final_pose"]["y"] == 3.0

    pos_task = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-pos-1",
            "session_id": "sess-001",
            "permissions": ["robot:position"],
            "skill": "get_position",
            "input": {},
        },
    )
    assert pos_task.status_code == 200
    pos_body = pos_task.json()
    assert pos_body["status"] == "SUCCEEDED"
    assert pos_body["data"]["x"] == 8.0
    assert pos_body["data"]["y"] == 3.0


def test_openclaw_permission_denied():
    denied = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-move-denied",
            "session_id": "sess-002",
            "permissions": ["robot:status"],
            "skill": "move_to",
            "input": {"location": "dock", "timeout_seconds": 3},
        },
    )
    assert denied.status_code == 403


def test_openclaw_idempotency_key_reuses_run():
    req = {
        "version": "1.0",
        "request_id": "req-cap-1",
        "idempotency_key": "cap-001",
        "session_id": "sess-003",
        "permissions": ["robot:camera"],
        "skill": "capture_image",
        "input": {"camera": "front"},
    }
    first = client.post("/v1/tasks", json=req)
    assert first.status_code == 200

    second = client.post(
        "/v1/tasks",
        json={**req, "request_id": "req-cap-2"},
    )
    assert second.status_code == 200
    assert second.json()["run_id"] == first.json()["run_id"]


def test_openclaw_move_requires_permission():
    denied = client.post(
        "/v1/tasks",
        json={
            "version": "1.0",
            "request_id": "req-move-no-perm",
            "session_id": "sess-004",
            "permissions": [],
            "skill": "move_to",
            "input": {"location": "dock", "timeout_seconds": 3},
        },
    )
    assert denied.status_code == 403
