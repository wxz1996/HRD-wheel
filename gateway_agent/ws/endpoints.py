import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gateway_context_service import get_gateway_context_service
from robot_services.motion.scripts.mqtt_motion_service import get_mqtt_motion_service
from security import authenticate_websocket

router = APIRouter()
# WS 状态/日志/识别通道共享的网关上下文。
gateway_context = get_gateway_context_service()
motion_service = get_mqtt_motion_service()


def _clamp_axis(value: float) -> float:
    return max(-1.0, min(1.0, value))


@router.websocket('/ws/state')
async def ws_state(ws: WebSocket):
    claims = await authenticate_websocket(ws)
    if not claims:
        return
    try:
        while True:
            s = gateway_context.get_state()
            await ws.send_text(json.dumps({'type': 'state', 'payload': s.model_dump(mode='json')}))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/logs')
async def ws_logs(ws: WebSocket):
    claims = await authenticate_websocket(ws)
    if not claims:
        return
    msgs = ['进入AR操控模块', '物件识别：开', '底盘控制输入', '网络波动告警']
    i = 0
    try:
        while True:
            log = gateway_context.make_log(msgs[i % len(msgs)], 'INFO' if i % 4 != 3 else 'WARN')
            await ws.send_text(json.dumps({'type': 'log', 'payload': log.model_dump(mode='json')}))
            i += 1
            await asyncio.sleep(1.2)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/vision')
async def ws_vision(ws: WebSocket):
    claims = await authenticate_websocket(ws)
    if not claims:
        return
    try:
        while True:
            await ws.send_text(
                json.dumps({
                    'type': 'vision_results',
                    'payload': {
                        'frameId': 'frame_001',
                        'targets': [t.model_dump(mode='json') for t in gateway_context.get_vision()],
                    },
                })
            )
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/control')
async def ws_control(ws: WebSocket):
    claims = await authenticate_websocket(ws)
    if not claims:
        return
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({'type': 'control_ack', 'payload': {'ok': False, 'error': 'invalid_json'}}))
                continue

            msg_type = str(msg.get('type', 'base_joystick'))
            payload = msg.get('payload') if isinstance(msg.get('payload'), dict) else {}
            try:
                x = _clamp_axis(float(payload.get('x', 0.0)))
                y = _clamp_axis(float(payload.get('y', 0.0)))
            except (TypeError, ValueError):
                x = 0.0
                y = 0.0

            if not motion_service.connected:
                await ws.send_text(
                    json.dumps({
                        'type': 'control_ack',
                        'payload': {
                            'ok': False,
                            'source': msg_type,
                            'error': 'motion_service_disconnected',
                            'applied': {'x': x, 'y': y},
                        },
                    })
                )
                continue

            command_ts = time.time()
            motion_service.send_drive_command(x=x, y=y, source=msg_type)
            ack = await asyncio.to_thread(motion_service.wait_for_ack, command_ts, 0.2)

            await ws.send_text(
                json.dumps({
                    'type': 'control_ack',
                    'payload': {
                        'ok': ack.ok if ack else True,
                        'source': msg_type,
                        'routed': 'mqtt',
                        'commandTopic': motion_service.command_topic,
                        'ackTopic': motion_service.ack_topic,
                        'ackPending': ack is None,
                        'applied': {'x': x, 'y': y},
                        'robotAck': ack.payload if ack else None,
                    },
                })
            )
    except WebSocketDisconnect:
        return
