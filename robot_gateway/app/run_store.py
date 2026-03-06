from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from .models import Artifact, Envelope, ErrorInfo, RunEvent, RunStatus


@dataclass
class RunRecord:
    run_id: str
    skill: str
    request_id: str
    idempotency_key: str | None = None
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
            version="1.0",
            request_id=self.request_id,
            idempotency_key=self.idempotency_key,
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

    def to_event(
        self,
        *,
        event: Literal["progress", "status_changed", "artifact_created", "log"],
        status: RunStatus | None = None,
        percent: int | None = None,
        message: str | None = None,
        telemetry: dict[str, Any] | None = None,
    ) -> RunEvent:
        return RunEvent(
            version="1.0",
            request_id=self.request_id,
            idempotency_key=self.idempotency_key,
            run_id=self.run_id,
            event=event,
            status=status or self.status,
            percent=percent,
            message=message,
            telemetry=telemetry,
        )


class RunPersistence(ABC):
    @abstractmethod
    def save(self, record: RunRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, run_id: str) -> RunRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_idempotency_key(self, key: str) -> RunRecord | None:
        raise NotImplementedError

    @abstractmethod
    def bind_idempotency_key(self, key: str, run_id: str) -> None:
        raise NotImplementedError


class InMemoryRunPersistence(RunPersistence):
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._idempotency_index: dict[str, str] = {}

    def save(self, record: RunRecord) -> None:
        self._runs[record.run_id] = record

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def get_by_idempotency_key(self, key: str) -> RunRecord | None:
        run_id = self._idempotency_index.get(key)
        if not run_id:
            return None
        return self._runs.get(run_id)

    def bind_idempotency_key(self, key: str, run_id: str) -> None:
        self._idempotency_index[key] = run_id


class RunStore:
    def __init__(self, persistence: RunPersistence | None = None) -> None:
        self._persistence = persistence or InMemoryRunPersistence()

    def create(
        self,
        *,
        skill: str,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[RunRecord, bool]:
        if idempotency_key:
            existing = self._persistence.get_by_idempotency_key(idempotency_key)
            if existing:
                if existing.skill != skill:
                    raise ValueError("idempotency_key already used by another skill")
                return existing, False

        run_id = str(uuid.uuid4())
        record = RunRecord(
            run_id=run_id,
            skill=skill,
            request_id=request_id or str(uuid.uuid4()),
            idempotency_key=idempotency_key,
        )
        self._persistence.save(record)
        if idempotency_key:
            self._persistence.bind_idempotency_key(idempotency_key, run_id)
        return record, True

    def get(self, run_id: str) -> RunRecord | None:
        return self._persistence.get(run_id)

    def update(self, record: RunRecord) -> RunRecord:
        self._persistence.save(record)
        return record

    def cancel(self, run_id: str) -> RunRecord | None:
        record = self._persistence.get(run_id)
        if not record:
            return None
        record.cancel_event.set()
        if record.status in (RunStatus.CREATED, RunStatus.RUNNING):
            record.status = RunStatus.CANCELED
            record.summary = "Run canceled"
        self._persistence.save(record)
        return record


run_store = RunStore()
