from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    robot_port: int = int(os.getenv("ROBOT_PORT", "8000"))
    default_camera_topic: str = os.getenv("DEFAULT_CAMERA_TOPIC", "/camera/image_raw")
    default_width: int = int(os.getenv("DEFAULT_WIDTH", "640"))
    default_height: int = int(os.getenv("DEFAULT_HEIGHT", "480"))
    default_fps: int = int(os.getenv("DEFAULT_FPS", "15"))
    stun_server: str | None = os.getenv("STUN_SERVER")


settings = Settings()
