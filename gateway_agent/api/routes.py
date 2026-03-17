import base64
import time
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from gateway_context_service import get_gateway_context_service
from robot_services.camera_monitor.scripts.mqtt_video_service import get_mqtt_video_service
from robot_services.manipulation.scripts.mqtt_manipulation_service import get_mqtt_manipulation_service
from robot_services.point_navigation.scripts.mqtt_point_navigation_service import get_mqtt_point_navigation_service
from robot_services.point_navigation.waypoints import get_waypoint, list_waypoints
from robot_services.vision.scripts.mqtt_vision_service import get_mqtt_vision_service
from security import (
    TOKEN_TTL_SECONDS,
    STREAM_TOKEN_TTL_SECONDS,
    issue_token,
    issue_video_stream_token,
    require_auth,
    require_stream_token_string,
    verify_login_credentials,
)

router = APIRouter(prefix='/api')
# 面向 Web 的状态/视觉/日志上下文（不负责机器人通信）
gateway_context = get_gateway_context_service()
# 面向 Robot 的视频通道（通过 MQTT）
video_service = get_mqtt_video_service()
manipulation_service = get_mqtt_manipulation_service()
navigation_service = get_mqtt_point_navigation_service()
vision_service = get_mqtt_vision_service()

_JPEG_PLACEHOLDER = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAQDAwQDAwQEAwQFBAQFBgoHBgYGBgkICQoK"
    "CgwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/2wBDAQUGBggICQkICQwMDAwM"
    "DAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAABAAED"
    "AREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAXAQADAQAAAAAAAAAAAAAAAA"
    "AAAgP/2gAMAwEAAhADEAAAAd0f/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ/"
    "/8QAFBEBAAAAAAAAAAAAAAAAAAAAEP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAA"
    "AAEP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAEP/aAAgBAQAGPwJ//8QAFBAB"
    "AAAAAAAAAAAAAAAAAAAAEP/aAAgBAQABPyF//9k="
)


class LoginReq(BaseModel):
    account: str
    password: str


class ToggleReq(BaseModel):
    enabled: bool


class SelectionReq(BaseModel):
    targetId: str


class NavigationGoalReq(BaseModel):
    targetName: str


class MonitorGasStoveTaskReq(BaseModel):
    targetName: str = "kitchen"


class InspectGasStoveTaskReq(BaseModel):
    targetName: str = "kitchen"
    smokeLevel: Literal["low", "high", "unknown"] = "unknown"


def _require_stream_access(authorization: str | None, token: str | None) -> dict:
    # 优先使用 query token 兼容 <img src=...> 的 MJPEG 场景；否则回退到 Authorization。
    if token:
        return require_stream_token_string(token)
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return require_stream_token_string(parts[1].strip())
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing auth token")


def _mjpeg_iter():
    last_seq = 0
    while True:
        seq, frame, _ = video_service.frames.wait_for_frame(last_seq, timeout_s=1.0)
        if seq > last_seq and frame:
            payload = frame
            last_seq = seq
        else:
            payload = _JPEG_PLACEHOLDER
            time.sleep(0.2)
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n"
            b"\r\n" + payload + b"\r\n"
        )


@router.post('/login')
def login(req: LoginReq):
    if not verify_login_credentials(req.account, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='invalid account or password',
        )
    token = issue_token(req.account)
    return {
        'success': True,
        'token': token,
        'expiresIn': TOKEN_TTL_SECONDS,
        'user': {'id': 'u_demo', 'name': req.account, 'role': 'operator'},
    }


@router.get('/me')
def me(claims: dict = Depends(require_auth)):
    return {'id': 'u_demo', 'name': claims.get('sub', 'demo'), 'role': claims.get('role', 'operator')}


@router.get('/robot/summary')
def robot_summary(_: dict = Depends(require_auth)):
    s = gateway_context.get_state()
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
        'logs': [gateway_context.make_log('登录成功').model_dump(mode='json')],
    }


@router.get('/ar/bootstrap')
def ar_bootstrap(_: dict = Depends(require_auth)):
    s = gateway_context.get_state()
    st = video_service.status()
    return {
        'robotId': s.robotId,
        'battery': s.battery,
        'latencyMs': s.latencyMs,
        'fps': s.fps,
        'recognitionEnabled': gateway_context.recognition_enabled,
        'videoMode': 'ros2_mqtt_stream',
        'videoConnected': st.connected,
        'videoTopic': st.topic,
    }


@router.post('/ar/recognition/toggle')
def toggle(req: ToggleReq, _: dict = Depends(require_auth)):
    enabled = gateway_context.toggle_recognition(req.enabled)
    return {'success': True, 'enabled': enabled}


@router.post('/ar/selection')
def selection(req: SelectionReq, _: dict = Depends(require_auth)):
    t = gateway_context.select_target(req.targetId)
    return {'success': True, 'target': {'id': t.id, 'label': t.label} if t else None}


@router.get('/navigation/waypoints')
def navigation_waypoints(_: dict = Depends(require_auth)):
    return {'items': list_waypoints()}


@router.get('/navigation/status')
def navigation_status(_: dict = Depends(require_auth)):
    st = navigation_service.status()
    return {
        'connected': st.connected,
        'commandTopic': st.command_topic,
        'statusTopic': st.status_topic,
        'activeGoalId': st.active_goal_id,
        'lastReport': st.last_report,
    }


@router.post('/navigation/goals')
def navigation_goals(req: NavigationGoalReq, _: dict = Depends(require_auth)):
    waypoint = get_waypoint(req.targetName)
    if waypoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'unknown waypoint: {req.targetName}',
        )

    goal_id = f'nav-{uuid4().hex[:8]}'
    navigation_service.send_goal(
        goal_id=goal_id,
        target_name=waypoint.name,
        x=waypoint.x,
        y=waypoint.y,
        yaw=waypoint.yaw,
        source='api',
    )
    return {
        'success': True,
        'goalId': goal_id,
        'target': {
            'name': waypoint.name,
            'x': waypoint.x,
            'y': waypoint.y,
            'yaw': waypoint.yaw,
            'description': waypoint.description,
        },
    }


@router.post('/navigation/goals/{goal_id}/cancel')
def navigation_cancel(goal_id: str, _: dict = Depends(require_auth)):
    navigation_service.cancel_goal(goal_id=goal_id, source='api')
    return {'success': True, 'goalId': goal_id}


@router.get('/vision/status')
def vision_status(_: dict = Depends(require_auth)):
    st = vision_service.status()
    return {
        'connected': st.connected,
        'commandTopic': st.command_topic,
        'statusTopic': st.status_topic,
        'activeTaskId': st.active_task_id,
        'lastReport': st.last_report,
    }


@router.post('/tasks/monitor-gas-stove')
def monitor_gas_stove(req: MonitorGasStoveTaskReq, _: dict = Depends(require_auth)):
    waypoint = get_waypoint(req.targetName)
    if waypoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'unknown waypoint: {req.targetName}',
        )

    workflow_id = f'task-{uuid4().hex[:8]}'
    nav_goal_id = f'nav-{uuid4().hex[:8]}'
    vision_task_id = f'vision-{uuid4().hex[:8]}'

    navigation_service.send_goal(
        goal_id=nav_goal_id,
        target_name=waypoint.name,
        x=waypoint.x,
        y=waypoint.y,
        yaw=waypoint.yaw,
        source='task:monitor-gas-stove',
    )
    vision_service.start_scene_monitor(
        task_id=vision_task_id,
        scene='gas_stove',
        target_name=waypoint.name,
        source='task:monitor-gas-stove',
    )

    return {
        'success': True,
        'workflowId': workflow_id,
        'target': {
            'name': waypoint.name,
            'x': waypoint.x,
            'y': waypoint.y,
            'yaw': waypoint.yaw,
            'description': waypoint.description,
        },
        'steps': [
            {
                'service': 'point_navigation',
                'status': 'dispatched',
                'goalId': nav_goal_id,
                'commandTopic': navigation_service.command_topic,
            },
            {
                'service': 'vision',
                'status': 'dispatched',
                'taskId': vision_task_id,
                'scene': 'gas_stove',
                'commandTopic': vision_service.command_topic,
            },
        ],
    }


@router.get('/manipulation/status')
def manipulation_status(_: dict = Depends(require_auth)):
    st = manipulation_service.status()
    return {
        'connected': st.connected,
        'commandTopic': st.command_topic,
        'statusTopic': st.status_topic,
        'activeTaskId': st.active_task_id,
        'lastReport': st.last_report,
    }


@router.post('/tasks/inspect-gas-stove')
def inspect_gas_stove(req: InspectGasStoveTaskReq, _: dict = Depends(require_auth)):
    waypoint = get_waypoint(req.targetName)
    if waypoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'unknown waypoint: {req.targetName}',
        )

    workflow_id = f'task-{uuid4().hex[:8]}'
    nav_goal_id = f'nav-{uuid4().hex[:8]}'
    vision_task_id = f'vision-{uuid4().hex[:8]}'

    navigation_service.send_goal(
        goal_id=nav_goal_id,
        target_name=waypoint.name,
        x=waypoint.x,
        y=waypoint.y,
        yaw=waypoint.yaw,
        source='task:inspect-gas-stove',
    )
    vision_service.start_scene_monitor(
        task_id=vision_task_id,
        scene='gas_stove',
        target_name=waypoint.name,
        source='task:inspect-gas-stove',
    )

    steps = [
        {
            'service': 'point_navigation',
            'status': 'dispatched',
            'goalId': nav_goal_id,
            'commandTopic': navigation_service.command_topic,
        },
        {
            'service': 'vision',
            'status': 'dispatched',
            'taskId': vision_task_id,
            'scene': 'gas_stove',
            'commandTopic': vision_service.command_topic,
        },
    ]

    next_action = 'continue_monitoring'
    manipulation_task_id = None
    if req.smokeLevel == 'high':
        manipulation_task_id = f'manip-{uuid4().hex[:8]}'
        manipulation_service.execute_action(
            task_id=manipulation_task_id,
            action_name='turn_off_gas_stove',
            target_name=waypoint.name,
            source='task:inspect-gas-stove',
        )
        steps.append(
            {
                'service': 'manipulation',
                'status': 'dispatched',
                'taskId': manipulation_task_id,
                'actionName': 'turn_off_gas_stove',
                'commandTopic': manipulation_service.command_topic,
            }
        )
        next_action = 'turn_off_gas_stove'

    return {
        'success': True,
        'workflowId': workflow_id,
        'target': {
            'name': waypoint.name,
            'x': waypoint.x,
            'y': waypoint.y,
            'yaw': waypoint.yaw,
            'description': waypoint.description,
        },
        'decision': {
            'smokeLevel': req.smokeLevel,
            'nextAction': next_action,
        },
        'steps': steps,
    }


@router.get('/video/status')
def video_status(_: dict = Depends(require_auth)):
    st = video_service.status()
    return {
        "connected": st.connected,
        "topic": st.topic,
        "frameSeq": st.frame_seq,
        "lastFrameTs": st.last_frame_ts,
        "source": st.source,
    }


@router.post('/video/token')
def issue_video_token(claims: dict = Depends(require_auth)):
    account = str(claims.get("sub", "operator"))
    token = issue_video_stream_token(account)
    return {
        "token": token,
        "expiresIn": STREAM_TOKEN_TTL_SECONDS,
        "scope": "video:stream",
    }


@router.get('/video/stream')
def video_stream(
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
):
    _require_stream_access(authorization=authorization, token=token)
    return StreamingResponse(
        _mjpeg_iter(),
        media_type='multipart/x-mixed-replace; boundary=frame',
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
