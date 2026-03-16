from __future__ import annotations

"""网关侧上下文服务（面向 Web 的状态/视觉/日志数据）。

本模块不负责机器人通信（MQTT/ROS2），只维护 API/WS 使用的内存上下文，
用于给前端提供稳定的数据结构。
"""

from datetime import datetime, timezone
from random import randint
from threading import Lock
from typing import Literal

from pydantic import BaseModel, Field


class Pose(BaseModel):
    x: float
    y: float
    yaw: float


class HeadState(BaseModel):
    pan: float
    tilt: float


class BaseState(BaseModel):
    speed: float
    direction: str = "fwd"


class RobotState(BaseModel):
    """前端机器人摘要状态模型。"""
    robotId: str = "robot-001"
    workStatus: str = "待机中"
    battery: int = 78
    latencyMs: int = 35
    fps: int = 28
    pose: Pose = Field(default_factory=lambda: Pose(x=1.2, y=0.5, yaw=0.3))
    head: HeadState = Field(default_factory=lambda: HeadState(pan=10, tilt=-5))
    base: BaseState = Field(default_factory=lambda: BaseState(speed=0.0))


class VisionTarget(BaseModel):
    """前端识别结果目标模型。"""
    id: str
    label: str
    bbox: tuple[int, int, int, int]
    score: float


class LogEntry(BaseModel):
    """前端日志流模型。"""
    ts: datetime
    level: Literal["INFO", "WARN", "ERROR"]
    message: str


class GatewayContextService:
    """REST 与 WebSocket 共享的网关内存上下文。

    职责：
    - 提供前端使用的数据模型（机器人摘要、识别目标、日志）
    - 维护网关侧上下文值（识别开关、选中目标）
    - 作为 API 与 WS 共同使用的单例上下文
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = RobotState()
        self._recognition_enabled = False
        self._selected_target_id: str | None = None

    def get_state(self) -> RobotState:
        """返回前端使用的机器人摘要状态。"""
        with self._lock:
            state = self._state
            state.battery = max(20, min(100, state.battery + randint(-1, 1)))
            state.latencyMs = max(20, min(90, state.latencyMs + randint(-3, 3)))
            state.fps = max(20, min(35, state.fps + randint(-1, 1)))
            state.pose.x = round(state.pose.x + 0.01, 2)
            state.pose.y = round(state.pose.y + 0.005, 2)
            return state

    def get_vision(self) -> list[VisionTarget]:
        """返回前端叠加层使用的识别目标列表。"""
        if not self._recognition_enabled:
            return []
        targets = self._vision_targets()
        if not self._selected_target_id:
            return targets
        return [
            t.model_copy(update={"score": round(min(0.99, t.score + 0.02), 2)})
            if t.id == self._selected_target_id
            else t
            for t in targets
        ]

    def toggle_recognition(self, enabled: bool) -> bool:
        """切换前端可见的识别开关状态。"""
        with self._lock:
            self._recognition_enabled = enabled
            if not enabled:
                self._selected_target_id = None
        return enabled

    def select_target(self, target_id: str) -> VisionTarget | None:
        """在网关上下文中记录前端选中的识别目标。"""
        with self._lock:
            self._selected_target_id = target_id
        return next((t for t in self._vision_targets() if t.id == target_id), None)

    @property
    def recognition_enabled(self) -> bool:
        return self._recognition_enabled

    @staticmethod
    def make_log(msg: str, level: str = "INFO") -> LogEntry:
        return LogEntry(ts=datetime.now(timezone.utc), level=level, message=msg)

    @staticmethod
    def _vision_targets() -> list[VisionTarget]:
        return [
            VisionTarget(id="obj_001", label="标准物料框", bbox=(120, 90, 260, 220), score=0.94),
            VisionTarget(id="obj_002", label="工具箱", bbox=(310, 180, 480, 350), score=0.89),
        ]


_gateway_context_singleton: GatewayContextService | None = None


def get_gateway_context_service() -> GatewayContextService:
    """返回进程级单例网关上下文服务。"""
    global _gateway_context_singleton
    if _gateway_context_singleton is None:
        _gateway_context_singleton = GatewayContextService()
    return _gateway_context_singleton
