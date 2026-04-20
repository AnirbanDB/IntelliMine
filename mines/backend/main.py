"""
Main FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.websocket import router as ws_router, start_streamer
from engine.simulation import SimulationEngine
from config import config

# Global Simulation Engine Instance
engine = SimulationEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize engine and start the background broadcaster
    engine.initialize()
    print("Initializing Mine Simulation...")
    start_streamer(app, engine)
    
    yield
    
    # Shutdown
    print("Shutting down...")

app = FastAPI(title="IntelliMine API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
