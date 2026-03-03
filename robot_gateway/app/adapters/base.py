from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RobotStatus:
    battery: float
    mode: str


class RobotAdapter:
    def get_status(self) -> RobotStatus:
        raise NotImplementedError
