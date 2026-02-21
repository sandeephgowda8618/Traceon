from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class CaseWSManager:
    def __init__(self):
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, case_id: str, ws: WebSocket):
        await ws.accept()
        self._rooms[case_id].add(ws)

    def disconnect(self, case_id: str, ws: WebSocket):
        self._rooms[case_id].discard(ws)

    async def broadcast(self, case_id: str, event: dict):
        dead = []
        for ws in self._rooms.get(case_id, set()):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._rooms[case_id].discard(ws)


ws_manager = CaseWSManager()
