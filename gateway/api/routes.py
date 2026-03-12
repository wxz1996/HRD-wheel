from fastapi import APIRouter
from pydantic import BaseModel

from mock import data
from services.bridge import RobotBridgeService

router = APIRouter(prefix='/api')
svc = RobotBridgeService(mode='mock')


class LoginReq(BaseModel):
    account: str
    password: str


class ToggleReq(BaseModel):
    enabled: bool


class SelectionReq(BaseModel):
    targetId: str


@router.post('/login')
def login(req: LoginReq):
    return {
        'success': True,
        'user': {'id': 'u_demo', 'name': req.account, 'role': 'operator'},
    }


@router.get('/me')
def me():
    return {'id': 'u_demo', 'name': 'demo', 'role': 'operator'}


@router.get('/robot/summary')
def robot_summary():
    s = svc.get_state()
    return {
        'robotId': s.robotId,
        'robotName': 'HRT Demo Robot',
        'workStatus': s.workStatus,
        'battery': s.battery,
        'statusSummary': {
            'pose': f'x={s.pose.x},y={s.pose.y},yaw={s.pose.yaw}',
            'head': f'pan={s.head.pan},tilt={s.head.tilt}',
            'base': f'spd={s.base.speed}',
        },
        'logs': [data.make_log('登录成功').model_dump(mode='json')],
    }


@router.get('/ar/bootstrap')
def ar_bootstrap():
    s = svc.get_state()
    return {
        'robotId': s.robotId,
        'battery': s.battery,
        'latencyMs': s.latencyMs,
        'fps': s.fps,
        'recognitionEnabled': data.recognition_enabled,
        'videoMode': 'mock',
    }


@router.post('/ar/recognition/toggle')
def toggle(req: ToggleReq):
    enabled = svc.toggle_recognition(req.enabled)
    return {'success': True, 'enabled': enabled}


@router.post('/ar/selection')
def selection(req: SelectionReq):
    t = svc.select_target(req.targetId)
    return {'success': True, 'target': {'id': t.id, 'label': t.label} if t else None}
