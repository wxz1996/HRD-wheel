from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class Pose(BaseModel):
    x: float
    y: float
    yaw: float


class HeadState(BaseModel):
    pan: float
    tilt: float


class BaseState(BaseModel):
    speed: float
    direction: str = '↗'


class RobotState(BaseModel):
    robotId: str = 'robot-001'
    workStatus: str = '待机中'
    battery: int = 78
    latencyMs: int = 35
    fps: int = 28
    pose: Pose = Pose(x=1.2, y=0.5, yaw=0.3)
    head: HeadState = HeadState(pan=10, tilt=-5)
    base: BaseState = BaseState(speed=0.0)


class VisionTarget(BaseModel):
    id: str
    label: str
    bbox: tuple[int, int, int, int]
    score: float


class LogEntry(BaseModel):
    ts: datetime
    level: Literal['INFO', 'WARN', 'ERROR']
    message: str


class ControlInput(BaseModel):
    type: Literal['base_joystick']
    payload: dict[str, float] = Field(default_factory=dict)
