"""
Full simulation state model — the complete snapshot emitted each tick.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .mine_graph import MineGraph
from .agents import Truck, Worker, Equipment
from .hazards import HazardEvent, SensorReading


class SimulationStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class ScheduleEntry(BaseModel):
    """A single entry in the CSP schedule output."""
    zone_id: str
    time_slot: int
    activity: str  # "blast", "drill", "load", "idle", "halted"
    equipment_id: Optional[str] = None


class PathResult(BaseModel):
    """Result of an A* path computation."""
    agent_id: str
    path: list[str]
    total_cost: float
    mode: str  # "normal", "hazard", "evacuation"


class SimulationState(BaseModel):
    """Complete simulation state — serialized and sent to frontend each tick."""
    tick: int = 0
    status: SimulationStatus = SimulationStatus.STOPPED
    graph: Optional[MineGraph] = None
    trucks: list[Truck] = Field(default_factory=list)
    workers: list[Worker] = Field(default_factory=list)
    equipment: list[Equipment] = Field(default_factory=list)
    active_hazards: list[HazardEvent] = Field(default_factory=list)
    sensor_readings: dict[str, SensorReading] = Field(default_factory=dict)
    hazard_probabilities: dict[str, float] = Field(default_factory=dict)
    schedule: list[ScheduleEntry] = Field(default_factory=list)
    paths: list[PathResult] = Field(default_factory=list)
    events_log: list[dict[str, Any]] = Field(default_factory=list)

    # Simulation parameters (mirrors config, user can override)
    parameters: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    def to_serializable(self) -> dict:
        return {
            "tick": self.tick,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "graph": self.graph.to_serializable() if self.graph else None,
            "trucks": [t.to_serializable() for t in self.trucks],
            "workers": [w.to_serializable() for w in self.workers],
            "equipment": [e.to_serializable() for e in self.equipment],
            "active_hazards": [h.to_serializable() for h in self.active_hazards],
            "sensor_readings": {
                k: v.to_serializable() for k, v in self.sensor_readings.items()
            },
            "hazard_probabilities": {
                k: round(v, 4) for k, v in self.hazard_probabilities.items()
            },
            "schedule": [
                {
                    "zone_id": s.get("zone_id") if isinstance(s, dict) else s.zone_id,
                    "time_slot": s.get("time_slot") if isinstance(s, dict) else s.time_slot,
                    "activity": s.get("activity") if isinstance(s, dict) else s.activity,
                    "equipment_id": s.get("equipment_id") if isinstance(s, dict) else s.equipment_id,
                }
                for s in self.schedule
            ],
            "paths": [
                {
                    "agent_id": p.get("agent_id") if isinstance(p, dict) else p.agent_id,
                    "path": p.get("path") if isinstance(p, dict) else p.path,
                    "total_cost": round(p.get("total_cost") if isinstance(p, dict) else p.total_cost, 2),
                    "mode": p.get("mode") if isinstance(p, dict) else p.mode,
                }
                for p in self.paths
            ],
            "events_log": self.events_log[-50:],  # last 50 events
            "parameters": self.parameters,
        }
