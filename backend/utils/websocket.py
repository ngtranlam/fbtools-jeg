from __future__ import annotations

import json
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: dict[str, Any]):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, data: dict[str, Any]):
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


ws_manager = ConnectionManager()
