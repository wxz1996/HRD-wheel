#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import socket
import time
from typing import Any

import paho.mqtt.client as mqtt
from PIL import Image, ImageDraw


def _reason_code_value(reason_code: Any) -> int:
    value = getattr(reason_code, "value", reason_code)
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def main() -> int:
    parser = argparse.ArgumentParser(description="Robot-side MQTT JSON agent stub (simulated ROS2 execution).")
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--topic-prefix", default="hrd")
    parser.add_argument("--robot-id", default="robot-001")
    parser.add_argument("--mqtt-username", default=None)
    parser.add_argument("--mqtt-password", default=None)
    args = parser.parse_args()

    topic_prefix = args.topic_prefix.rstrip("/")
    cmd_topic = f"{topic_prefix}/robot/{args.robot_id}/cmd"

    pose = {"frame_id": "map", "x": 2.4, "y": 1.1, "yaw": 0.2}

    def build_ok(correlation_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocol": "mqtt-json-v1",
            "timestamp": int(time.time()),
            "correlation_id": correlation_id,
            "ok": True,
            "data": data,
        }

    def build_err(correlation_id: str, error: str) -> dict[str, Any]:
        return {
            "protocol": "mqtt-json-v1",
            "timestamp": int(time.time()),
            "correlation_id": correlation_id,
            "ok": False,
            "error": error,
        }

    def on_connect(
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        del properties
        if _reason_code_value(reason_code) != 0:
            print(f"[agent] mqtt connect failed reason_code={reason_code}")
            return
        client.subscribe(cmd_topic, qos=1)
        print(f"[agent] subscribed: {cmd_topic}")

    def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        nonlocal pose
        try:
            req = json.loads(msg.payload.decode("utf-8"))
        except Exception as exc:
            print(f"[agent] invalid json: {exc}")
            return

        correlation_id = str(req.get("correlation_id", ""))
        reply_to = str(req.get("reply_to", ""))
        action = str(req.get("action", ""))
        payload = req.get("payload", {}) or {}

        if not correlation_id or not reply_to:
            print("[agent] missing correlation_id or reply_to")
            return

        if action == "get_status":
            resp = build_ok(correlation_id, {"battery": 0.76, "mode": "AUTO"})
        elif action == "get_position":
            resp = build_ok(correlation_id, pose)
        elif action == "move_to":
            target_pose = payload.get("pose")
            if target_pose:
                pose = {
                    "frame_id": target_pose.get("frame_id", "map"),
                    "x": float(target_pose.get("x", 0.0)),
                    "y": float(target_pose.get("y", 0.0)),
                    "yaw": float(target_pose.get("yaw", 0.0)),
                }
            else:
                # fixed mapping for named target
                pose = {"frame_id": "map", "x": 5.0, "y": 2.0, "yaw": 1.57}
            resp = build_ok(
                correlation_id,
                {
                    "accepted": True,
                    "message": "ROS2 nav command accepted and completed",
                    "final_pose": pose,
                    "ros2_meta": {
                        "adapter": "mqtt_json_agent_stub",
                        "action_server": "/navigate_to_pose",
                        "goal_id": f"goal-{int(time.time())}",
                        "result_code": 0,
                    },
                },
            )
        elif action == "capture_image":
            image = Image.new("RGB", (640, 480), color=(30, 30, 30))
            draw = ImageDraw.Draw(image)
            draw.text((20, 20), f"camera={payload.get('camera', 'front')}", fill=(255, 255, 255))
            draw.text((20, 55), f"robot_id={args.robot_id}", fill=(200, 255, 200))
            draw.text((20, 90), time.strftime("%Y-%m-%d %H:%M:%S"), fill=(200, 200, 255))
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            resp = build_ok(
                correlation_id,
                {
                    "camera": str(payload.get("camera", "front")),
                    "mime": "image/jpeg",
                    "width": 640,
                    "height": 480,
                    "image_jpeg_base64": base64.b64encode(buf.getvalue()).decode("ascii"),
                },
            )
        else:
            resp = build_err(correlation_id, f"unknown action {action}")

        client.publish(reply_to, json.dumps(resp, ensure_ascii=False), qos=1)
        print(f"[agent] action={action} correlation_id={correlation_id} reply_to={reply_to}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"robot-agent-stub-{args.robot_id}",
        clean_session=True,
    )
    if args.mqtt_username:
        client.username_pw_set(args.mqtt_username, args.mqtt_password)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(args.mqtt_host, args.mqtt_port, keepalive=30)
    except ConnectionRefusedError:
        print(
            f"[agent] cannot connect to MQTT broker at {args.mqtt_host}:{args.mqtt_port} "
            "(connection refused). Start broker first, e.g. `docker compose up -d mqtt-broker`."
        )
        return 1
    except socket.gaierror as exc:
        print(f"[agent] cannot resolve MQTT host {args.mqtt_host!r}: {exc}")
        return 1
    except OSError as exc:
        print(f"[agent] mqtt connection failed {args.mqtt_host}:{args.mqtt_port}: {exc}")
        return 1
    print(
        "[agent] started with "
        f"mqtt={args.mqtt_host}:{args.mqtt_port} topic_prefix={topic_prefix} robot_id={args.robot_id}"
    )
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[agent] stopped by user")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
