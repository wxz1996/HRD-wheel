from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .models import Artifact, Envelope, ErrorInfo, RunStatus


@dataclass
class RunRecord:
    run_id: str
    skill: str
    status: RunStatus = RunStatus.CREATED
    summary: str = ""
    text: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    telemetry: dict[str, Any] = field(default_factory=dict)
    error: ErrorInfo | None = None
    created_at: float = field(default_factory=time.time)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def to_envelope(self) -> Envelope:
        return Envelope(
            ok=self.status not in (RunStatus.FAILED,),
            skill=self.skill,
            run_id=self.run_id,
            status=self.status,
            summary=self.summary,
            text=self.text,
            data=self.data,
            artifacts=self.artifacts,
            telemetry=self.telemetry,
            error=self.error,
        )


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, skill: str) -> RunRecord:
        run_id = str(uuid.uuid4())
        record = RunRecord(run_id=run_id, skill=skill)
        self._runs[run_id] = record
        return record

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def cancel(self, run_id: str) -> RunRecord | None:
        record = self._runs.get(run_id)
        if not record:
            return None
        record.cancel_event.set()
        if record.status in (RunStatus.CREATED, RunStatus.RUNNING):
            record.status = RunStatus.CANCELED
            record.summary = "Run canceled"
        return record


run_store = RunStore()
