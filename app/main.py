"""FastAPI application for the automated radio dispatch simulator."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .dispatch import DispatchEngine
from .models import StatusBoard, SystemStatus, TrafficIn, utc_now
from .storage import DispatchStore

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

store = DispatchStore()
engine = DispatchEngine(store)
clients: set[WebSocket] = set()
clients_lock = asyncio.Lock()


async def broadcast(payload: dict[str, Any]) -> None:
    async with clients_lock:
        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead.append(client)
        for client in dead:
            clients.discard(client)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await store.connect()
    yield


app = FastAPI(
    title="Maritime Coast Radio Simulator",
    description="Maritime radio simulator with Mayday, Pan Pan, and Sécurité handling.",
    version=__version__,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/status", response_model=SystemStatus)
async def status() -> SystemStatus:
    return SystemStatus(listening=False, channel="VHF Ch 16", message="Ready for traffic")


@app.get("/api/log")
async def get_log(limit: int = 100) -> dict[str, Any]:
    entries = await store.list_logs(limit=limit)
    return {"entries": [entry.model_dump(mode="json") for entry in entries]}


@app.get("/api/units", response_model=StatusBoard)
async def get_units() -> StatusBoard:
    units = await store.list_units()
    return StatusBoard(units=units, updated_at=utc_now())


@app.post("/api/dispatch")
async def dispatch(traffic: TrafficIn) -> dict[str, Any]:
    reply = await engine.handle_traffic(traffic)
    units = await store.list_units()
    payload = {
        "type": "dispatch_event",
        "reply": reply.model_dump(mode="json"),
        "units": [unit.model_dump(mode="json") for unit in units],
    }
    await broadcast(payload)
    return payload


@app.delete("/api/reset")
async def reset() -> dict[str, str]:
    await store.clear_all()
    await broadcast({"type": "reset"})
    return {"status": "cleared"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    async with clients_lock:
        clients.add(websocket)
    try:
        while True:
            # Keepalive / ignore inbound client pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with clients_lock:
            clients.discard(websocket)
