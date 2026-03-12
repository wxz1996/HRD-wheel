from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket

from .models import RunEvent


class WSManager:
    def __init__(self) -> None:
        self._sockets: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, run_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._sockets[run_id].add(ws)

    def disconnect(self, run_id: str, ws: WebSocket) -> None:
        self._sockets[run_id].discard(ws)
        if not self._sockets[run_id]:
            self._sockets.pop(run_id, None)

    async def publish(self, event: RunEvent) -> None:
        stale: list[WebSocket] = []
        for ws in self._sockets.get(event.run_id, set()):
            try:
                await ws.send_json(event.model_dump())
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(event.run_id, ws)


ws_manager = WSManager()
