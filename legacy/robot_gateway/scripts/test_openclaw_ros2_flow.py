#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import uuid
from typing import Any

import httpx


TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELED"}


def submit_task(
    client: httpx.Client,
    *,
    base_url: str,
    session_id: str,
    skill: str,
    permissions: list[str],
    payload: dict[str, Any],
    request_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "version": "1.0",
        "request_id": request_id or f"req-{uuid.uuid4().hex[:10]}",
        "session_id": session_id,
        "permissions": permissions,
        "skill": skill,
        "input": payload,
    }
    if idempotency_key:
        body["idempotency_key"] = idempotency_key
    resp = client.post(f"{base_url}/v1/tasks", json=body)
    resp.raise_for_status()
    return resp.json()


def wait_task_done(
    client: httpx.Client,
    *,
    base_url: str,
    run_id: str,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        resp = client.get(f"{base_url}/v1/tasks/{run_id}")
        resp.raise_for_status()
        body = resp.json()
        if body["status"] in TERMINAL_STATUSES:
            return body
        time.sleep(0.2)
    raise TimeoutError(f"task {run_id} not finished in {timeout_seconds} seconds")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Virtual OpenClaw E2E test via Robot Gateway (mqtt_json)."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Gateway base URL")
    parser.add_argument("--session-id", default="openclaw-sim-session", help="Virtual OpenClaw session id")
    parser.add_argument("--timeout-seconds", type=float, default=25.0, help="Task polling timeout")
    parser.add_argument(
        "--expected-adapter",
        default="mqtt_json",
        help="Expected diagnostics adapter value (default: mqtt_json)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    session_id = args.session_id

    with httpx.Client(timeout=20.0) as client:
        print("[1/6] Query capabilities")
        caps = client.get(f"{base_url}/v1/capabilities")
        caps.raise_for_status()
        caps_body = caps.json()
        print(json.dumps(caps_body, ensure_ascii=False, indent=2))

        print("[2/6] Run robot link diagnostics")
        diag = client.get(f"{base_url}/v1/diagnostics/robot-link")
        diag.raise_for_status()
        diag_body = diag.json()
        print(json.dumps(diag_body, ensure_ascii=False, indent=2))
        if diag_body.get("adapter") != args.expected_adapter:
            raise AssertionError(
                f"expected adapter {args.expected_adapter}, got {diag_body.get('adapter')}"
            )

        print("[3/6] Get robot status")
        status_created = submit_task(
            client,
            base_url=base_url,
            session_id=session_id,
            skill="get_status",
            permissions=["robot:status"],
            payload={},
        )
        status_done = wait_task_done(
            client,
            base_url=base_url,
            run_id=status_created["run_id"],
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(status_done, ensure_ascii=False, indent=2))
        expected_mode = "AUTO"
        if status_done.get("data", {}).get("mode") != expected_mode:
            raise AssertionError(f"unexpected robot mode, expected {expected_mode}")

        print("[4/6] Get robot position")
        pos_created = submit_task(
            client,
            base_url=base_url,
            session_id=session_id,
            skill="get_position",
            permissions=["robot:position"],
            payload={},
        )
        pos_before = wait_task_done(
            client,
            base_url=base_url,
            run_id=pos_created["run_id"],
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(pos_before, ensure_ascii=False, indent=2))

        print("[5/6] Send move command")
        target_pose = {"frame_id": "map", "x": 8.0, "y": 3.0, "yaw": 0.5}
        move_created = submit_task(
            client,
            base_url=base_url,
            session_id=session_id,
            skill="move_to",
            permissions=["robot:move"],
            payload={"pose": target_pose, "timeout_seconds": 4},
            idempotency_key=f"move-{uuid.uuid4().hex[:8]}",
        )
        move_done = wait_task_done(
            client,
            base_url=base_url,
            run_id=move_created["run_id"],
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(move_done, ensure_ascii=False, indent=2))

        print("[6/6] Verify robot position updated")
        pos_created_after = submit_task(
            client,
            base_url=base_url,
            session_id=session_id,
            skill="get_position",
            permissions=["robot:position"],
            payload={},
        )
        pos_after = wait_task_done(
            client,
            base_url=base_url,
            run_id=pos_created_after["run_id"],
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(pos_after, ensure_ascii=False, indent=2))

        final_pose = pos_after.get("data", {})
        if final_pose.get("x") != target_pose["x"] or final_pose.get("y") != target_pose["y"]:
            raise AssertionError("position check failed: move command was not reflected")

    print("OpenClaw virtual flow PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
