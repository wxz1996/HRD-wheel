from datetime import datetime, timezone
from random import randint

from schemas.models import RobotState, VisionTarget, LogEntry


state = RobotState()
recognition_enabled = False
selected_target_id: str | None = None


def tick_state() -> RobotState:
    state.battery = max(20, min(100, state.battery + randint(-1, 1)))
    state.latencyMs = max(20, min(90, state.latencyMs + randint(-3, 3)))
    state.fps = max(20, min(35, state.fps + randint(-1, 1)))
    state.pose.x = round(state.pose.x + 0.01, 2)
    state.pose.y = round(state.pose.y + 0.005, 2)
    return state


def vision_targets() -> list[VisionTarget]:
    return [
        VisionTarget(id='obj_001', label='标准物料框', bbox=(120, 90, 260, 220), score=0.94),
        VisionTarget(id='obj_002', label='工具箱', bbox=(310, 180, 480, 350), score=0.89),
    ]


def make_log(msg: str, level: str = 'INFO') -> LogEntry:
    return LogEntry(ts=datetime.now(timezone.utc), level=level, message=msg)
