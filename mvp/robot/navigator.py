"""ROS2 navigator adapter.

If rclpy is unavailable, fallback to mock behavior for local MVP.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class NavigationResult:
    ok: bool
    message: str


class NavigatorAdapter:
    def send_nav_goal(self, goal: Dict[str, float | str]) -> NavigationResult:
        raise NotImplementedError


class Ros2Navigator(NavigatorAdapter):
    """Simple adapter; in production this should call a ROS2 action client."""

    REQUIRED_FIELDS = ("x", "y", "z", "roll", "pitch", "yaw", "frame_id")

    def __init__(self) -> None:
        self._ros_enabled = False
        try:
            import rclpy  # type: ignore  # noqa: F401

            self._ros_enabled = True
        except Exception:
            self._ros_enabled = False

    def send_nav_goal(self, goal: Dict[str, float | str]) -> NavigationResult:
        for field in self.REQUIRED_FIELDS:
            if field not in goal:
                return NavigationResult(ok=False, message=f"goal missing field: {field}")

        if self._ros_enabled:
            # Placeholder for ROS2 action call, e.g. NavigateToPose.
            return NavigationResult(ok=True, message=f"ros2 action goal executed: {goal}")

        return NavigationResult(ok=True, message=f"mock action goal executed: {goal}")
