from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


EventType = Literal["command", "vision", "system"]
EventSource = Literal["speech", "vision", "frontend", "system"]
VALID_ACTIONS = {
    "next_slide",
    "previous_slide",
    "save_board",
    "focus_start",
    "focus_stop",
    "start_presentation",
    "end_presentation",
    "frame_received",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EventType
    action: str
    source: EventSource
    timestamp: float = Field(default_factory=time)
    payload: dict[str, Any] = Field(default_factory=dict)


class CommandRequest(BaseModel):
    action: str
    source: EventSource = "frontend"
    payload: dict[str, Any] = Field(default_factory=dict)


class VisionFrameRequest(BaseModel):
    source: EventSource = "vision"
    image_b64: str | None = None
    gesture: str | None = None
    detected_objects: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    vision: bool
    speech: bool
    websocket_clients: int


@dataclass
class SessionState:
    session_id: str = "default"
    active: bool = True
    focus_mode: bool = False
    last_captured_frame: str | None = None
    timeline: deque[Event] = field(default_factory=lambda: deque(maxlen=500))
    last_trigger_by_source_action: dict[tuple[str, str], float] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "active": self.active,
            "focus_mode": self.focus_mode,
            "last_captured_frame": self.last_captured_frame,
            "timeline_size": len(self.timeline),
            "recent_events": [event.model_dump() for event in list(self.timeline)[-20:]],
        }


class SessionStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.base_dir / session_id

    def _images_dir(self, session_id: str) -> Path:
        images_dir = self._session_dir(session_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    async def persist_events(self, session: SessionState) -> None:
        session_dir = self._session_dir(session.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        events_path = session_dir / "events.json"
        payload = {
            "session_id": session.session_id,
            "active": session.active,
            "focus_mode": session.focus_mode,
            "last_captured_frame": session.last_captured_frame,
            "timeline": [event.model_dump() for event in session.timeline],
        }
        await asyncio.to_thread(events_path.write_text, json.dumps(payload, indent=2), "utf-8")

    async def save_frame(self, session_id: str, image_b64: str) -> str:
        image_bytes = base64.b64decode(image_b64)
        image_name = f"frame_{int(time() * 1000)}.png"
        image_path = self._images_dir(session_id) / image_name
        await asyncio.to_thread(image_path.write_bytes, image_bytes)
        return str(image_path)


class SessionManager:
    def __init__(self, storage: SessionStorage) -> None:
        self._session = SessionState()
        self._lock = asyncio.Lock()
        self._storage = storage

    async def get_session(self) -> SessionState:
        return self._session

    async def append_event(self, event: Event) -> None:
        async with self._lock:
            self._session.timeline.append(event)
            self._session.last_trigger_by_source_action[(event.source, event.action)] = event.timestamp
            snapshot = self._session
        await self._storage.persist_events(snapshot)

    async def set_focus_mode(self, enabled: bool) -> None:
        async with self._lock:
            self._session.focus_mode = enabled
            snapshot = self._session
        await self._storage.persist_events(snapshot)

    async def set_last_frame(self, image_path: str | None) -> None:
        async with self._lock:
            self._session.last_captured_frame = image_path
            snapshot = self._session
        await self._storage.persist_events(snapshot)

    async def save_frame(self, image_b64: str) -> str:
        image_path = await self._storage.save_frame(self._session.session_id, image_b64)
        await self.set_last_frame(image_path)
        return image_path

    async def last_triggered_at(self, source: str, action: str) -> float | None:
        return self._session.last_trigger_by_source_action.get((source, action))


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale_connections: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except RuntimeError:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)


class PresentationController:
    async def send(self, action: str) -> dict[str, Any]:
        key_map = {
            "next_slide": "right",
            "previous_slide": "left",
            "start_presentation": "f5",
            "end_presentation": "esc",
        }
        return {
            "status": "queued",
            "action": action,
            "mapped_key": key_map.get(action),
        }


class EventProcessor:
    def __init__(
        self,
        session_manager: SessionManager,
        connection_manager: ConnectionManager,
        presentation_controller: PresentationController,
    ) -> None:
        self.session_manager = session_manager
        self.connection_manager = connection_manager
        self.presentation_controller = presentation_controller
        self.cooldowns = {
            "next_slide": 1.0,
            "previous_slide": 1.0,
            "save_board": 2.0,
        }

    async def process(self, event: Event) -> dict[str, Any]:
        logger.info("Processing event: %s from %s", event.action, event.source)
        normalized_event = await self._normalize_event(event)
        await self._validate_event(normalized_event)

        session = await self.session_manager.get_session()
        side_effects: dict[str, Any] = {}

        if normalized_event.action == "focus_start":
            await self.session_manager.set_focus_mode(True)
        elif normalized_event.action == "focus_stop":
            await self.session_manager.set_focus_mode(False)
        elif normalized_event.action == "save_board":
            if not session.last_captured_frame:
                raise HTTPException(status_code=409, detail="no_board_frame_available")
            side_effects["board_saved"] = {
                "status": "queued",
                "timestamp": normalized_event.timestamp,
            }
        elif normalized_event.action in {"next_slide", "previous_slide", "start_presentation", "end_presentation"}:
            side_effects["presentation"] = await self.presentation_controller.send(normalized_event.action)

        await self.session_manager.append_event(normalized_event)

        outbound = {
            "type": "timeline_update",
            "data": {
                "event": normalized_event.model_dump(),
                "session": session.snapshot(),
                "side_effects": side_effects,
            },
        }
        await self.connection_manager.broadcast(outbound)

        return {
            "accepted": True,
            "event": normalized_event,
            "side_effects": side_effects,
        }

    async def _normalize_event(self, event: Event) -> Event:
        gesture_map = {
            "gesture_next_slide": "next_slide",
            "gesture_previous_slide": "previous_slide",
            "gesture_save_board": "save_board",
        }
        action = gesture_map.get(event.action, event.action)
        return event.model_copy(update={"action": action})

    async def _validate_event(self, event: Event) -> None:
        if event.action not in VALID_ACTIONS:
            raise HTTPException(status_code=400, detail="invalid_action")

        last_triggered_at = await self.session_manager.last_triggered_at(event.source, event.action)
        cooldown = self.cooldowns.get(event.action)
        if cooldown is not None and last_triggered_at is not None:
            if event.timestamp - last_triggered_at < cooldown:
                raise HTTPException(status_code=429, detail=f"{event.action}_cooldown_active")


app = FastAPI(title="Presentify-Air Backend", version="0.1.0")

storage = SessionStorage(Path(__file__).resolve().parent / "sessions")
session_manager = SessionManager(storage)
connection_manager = ConnectionManager()
presentation_controller = PresentationController()
event_processor = EventProcessor(session_manager, connection_manager, presentation_controller)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        vision=True,
        speech=True,
        websocket_clients=len(connection_manager.active_connections),
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    session = await session_manager.get_session()
    if session.session_id != session_id:
        raise HTTPException(status_code=404, detail="session_not_found")
    return session.snapshot()


@app.post("/command")
async def command(request: CommandRequest) -> dict[str, Any]:
    event = Event(type="command", action=request.action, source=request.source, payload=request.payload)
    result = await event_processor.process(event)
    return {
        "status": "ok",
        "event": result["event"].model_dump(),
        "side_effects": result["side_effects"],
    }


@app.post("/focus/start")
async def focus_start() -> dict[str, Any]:
    event = Event(type="system", action="focus_start", source="frontend")
    result = await event_processor.process(event)
    return {"status": "ok", "event": result["event"].model_dump()}


@app.post("/focus/stop")
async def focus_stop() -> dict[str, Any]:
    event = Event(type="system", action="focus_stop", source="frontend")
    result = await event_processor.process(event)
    return {"status": "ok", "event": result["event"].model_dump()}


@app.post("/save-board")
async def save_board() -> dict[str, Any]:
    event = Event(type="command", action="save_board", source="frontend")
    result = await event_processor.process(event)
    return {
        "status": "ok",
        "event": result["event"].model_dump(),
        "side_effects": result["side_effects"],
    }


@app.post("/vision/frame")
async def vision_frame(request: VisionFrameRequest) -> dict[str, Any]:
    image_path: str | None = None
    if request.image_b64:
        image_path = await session_manager.save_frame(request.image_b64)

    action = request.gesture or "frame_received"
    payload = {
        "detected_objects": request.detected_objects,
        "image_path": image_path,
        **request.payload,
    }
    event = Event(type="vision", action=action, source=request.source, payload=payload)
    result = await event_processor.process(event)
    return {
        "status": "ok",
        "event": result["event"].model_dump(),
        "side_effects": result["side_effects"],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await connection_manager.connect(websocket)
    session = await session_manager.get_session()
    await websocket.send_json({"type": "session_snapshot", "data": session.snapshot()})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
