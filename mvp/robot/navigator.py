"""ROS2 navigator adapter.

If rclpy is unavailable, fallback to mock behavior for local MVP.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class NavigationResult:
    ok: bool
    message: str


class NavigatorAdapter:
    def move_chassis(self, twist: List[float]) -> NavigationResult:
        raise NotImplementedError


class Ros2Navigator(NavigatorAdapter):
    """Simple adapter; in production this would publish to /cmd_vel or nav2 action."""

    def __init__(self) -> None:
        self._ros_enabled = False
        try:
            import rclpy  # type: ignore  # noqa: F401

            self._ros_enabled = True
        except Exception:
            self._ros_enabled = False

    def move_chassis(self, twist: List[float]) -> NavigationResult:
        if len(twist) != 6:
            return NavigationResult(ok=False, message="twist must have 6 dimensions")

        if self._ros_enabled:
            # Placeholder for ROS2 publish/action call.
            # Example: publish geometry_msgs/Twist to /cmd_vel.
            return NavigationResult(ok=True, message=f"ros2 navigation executed: {twist}")

        return NavigationResult(ok=True, message=f"mock navigation executed: {twist}")
