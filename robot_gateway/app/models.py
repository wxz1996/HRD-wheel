from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class RunStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class Artifact(BaseModel):
    type: Literal["image", "video", "webrtc", "file", "log", "trace"]
    mime: str | None = None
    url: str | None = None
    expires_at: int | None = None
    meta: dict[str, Any] | None = None


class ErrorInfo(BaseModel):
    code: int
    message: str
    recovery_hint: str | None = None
    details: dict[str, Any] | None = None


class Envelope(BaseModel):
    ok: bool
    skill: str
    run_id: str
    status: RunStatus
    summary: str = ""
    text: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    error: ErrorInfo | None = None


class Pose(BaseModel):
    frame_id: str | None = None
    x: float
    y: float
    yaw: float


class MoveToRequest(BaseModel):
    location: str | None = None
    pose: Pose | None = None
    timeout_seconds: int = 30

    @model_validator(mode="after")
    def check_target(cls, v: "MoveToRequest") -> "MoveToRequest":
        if not v.location and not v.pose:
            raise ValueError("Either location or pose is required")
        if not (1 <= v.timeout_seconds <= 600):
            raise ValueError("timeout_seconds must be in 1..600")
        return v


class CaptureImageRequest(BaseModel):
    camera: str = "front"


class GetStatusRequest(BaseModel):
    pass


class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: Literal["offer"]
    camera_topic: str | None = None
    width: int | None = None
    height: int | None = None
    fps: int | None = None


class WebRTCOfferResponse(BaseModel):
    sdp: str
    type: Literal["answer"]
    session_id: str


class RunEvent(BaseModel):
    run_id: str
    event: Literal["progress", "status_changed", "artifact_created", "log"]
    status: RunStatus
    percent: int | None = None
    message: str | None = None
    telemetry: dict[str, Any] | None = None
