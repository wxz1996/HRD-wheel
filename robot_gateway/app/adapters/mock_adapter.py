from __future__ import annotations

import random

from .base import RobotAdapter, RobotStatus


class MockRobotAdapter(RobotAdapter):
    def get_status(self) -> RobotStatus:
        return RobotStatus(battery=round(random.uniform(0.5, 0.95), 2), mode="idle")


mock_adapter = MockRobotAdapter()
