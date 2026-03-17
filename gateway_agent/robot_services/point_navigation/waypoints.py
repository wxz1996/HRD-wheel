from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Waypoint:
    name: str
    x: float
    y: float
    yaw: float
    description: str | None = None


_WAYPOINTS: dict[str, Waypoint] = {
    "kitchen": Waypoint(
        name="kitchen",
        x=2.5,
        y=1.2,
        yaw=0.0,
        description="Placeholder kitchen waypoint for future navigation workflow.",
    ),
}


def list_waypoints() -> list[dict[str, object]]:
    return [asdict(waypoint) for waypoint in _WAYPOINTS.values()]


def get_waypoint(name: str) -> Waypoint | None:
    return _WAYPOINTS.get(name)
