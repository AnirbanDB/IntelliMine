"""
WebSocket Handler

Manages real-time state streaming to connected clients.
"""
import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engine.simulation import SimulationEngine
from models.simulation_state import SimulationStatus

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        msg_str = json.dumps(message, default=str)
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_str)
            except Exception:
                dead.append(connection)
        for c in dead:
            self.disconnect(c)


manager = ConnectionManager()


async def state_streamer(engine: SimulationEngine):
    """Background task: tick the engine and broadcast state."""
    while True:
        try:
            if engine.state.status == SimulationStatus.RUNNING:
                engine.tick()

            # Always broadcast so the frontend stays in sync
            state_dict = engine.state.to_serializable()
            await manager.broadcast(state_dict)

            # Honour dynamic tick rate
            tick_rate_ms = (
                engine.state.parameters
                .get("simulation", {})
                .get("tick_rate_ms", 500)
            )
            await asyncio.sleep(max(0.05, tick_rate_ms / 1000.0))

        except Exception as e:
            print(f"[streamer] error: {e}")
            await asyncio.sleep(1)


@router.websocket("/live-state")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    from main import engine  # late import
    try:
        # Push current state immediately on connect
        await websocket.send_text(
            json.dumps(engine.state.to_serializable(), default=str)
        )
        # Keep connection open; parameter updates go through REST
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def start_streamer(_app, engine: SimulationEngine):
    """Called from the FastAPI lifespan to launch the background broadcaster."""
    asyncio.create_task(state_streamer(engine))
