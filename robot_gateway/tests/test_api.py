from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def wait_until_done(run_id: str, timeout: float = 8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in {"SUCCEEDED", "FAILED", "CANCELED"}:
            return resp.json()
        time.sleep(0.2)
    raise AssertionError("run did not finish in time")


def test_move_to_succeeds():
    resp = client.post("/skills/move_to:run", json={"location": "dock", "timeout_seconds": 3})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    final = wait_until_done(run_id)
    assert final["status"] == "SUCCEEDED"


def test_cancel_move_to():
    resp = client.post("/skills/move_to:run", json={"location": "station", "timeout_seconds": 20})
    run_id = resp.json()["run_id"]

    time.sleep(0.5)
    cancel = client.post(f"/runs/{run_id}:cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELED"


def test_capture_image_artifact_accessible():
    resp = client.post("/skills/capture_image:run", json={"camera": "front"})
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
