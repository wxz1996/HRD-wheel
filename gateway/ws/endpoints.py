import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mock import data
from services.bridge import RobotBridgeService

router = APIRouter()
svc = RobotBridgeService(mode='mock')


@router.websocket('/ws/state')
async def ws_state(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            s = svc.get_state()
            await ws.send_text(json.dumps({'type': 'state', 'payload': s.model_dump(mode='json')}))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/logs')
async def ws_logs(ws: WebSocket):
    await ws.accept()
    msgs = ['进入AR操控模块', '物件识别：开', '底盘控制输入', '网络波动告警']
    i = 0
    try:
        while True:
            log = data.make_log(msgs[i % len(msgs)], 'INFO' if i % 4 != 3 else 'WARN')
            await ws.send_text(json.dumps({'type': 'log', 'payload': log.model_dump(mode='json')}))
            i += 1
            await asyncio.sleep(1.2)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/vision')
async def ws_vision(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_text(
                json.dumps({
                    'type': 'vision_results',
                    'payload': {
                        'frameId': 'frame_001',
                        'targets': [t.model_dump(mode='json') for t in svc.get_vision()],
                    },
                })
            )
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/control')
async def ws_control(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            await ws.send_text(
                json.dumps({
                    'type': 'control_ack',
                    'payload': {'ok': True, 'source': msg.get('type', 'unknown')},
                })
            )
    except WebSocketDisconnect:
        return
