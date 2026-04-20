"""
Agent models: Trucks, Workers, Equipment.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    IDLE = "idle"
    MOVING = "moving"
    LOADING = "loading"
    UNLOADING = "unloading"
    WORKING = "working"
    EVACUATING = "evacuating"
    WAITING = "waiting"


class EquipmentType(str, Enum):
    DRILL = "drill"
    LOADER = "loader"
    VENTILATOR = "ventilator"


class Truck(BaseModel):
    """Mining truck that moves along paths, carries ore."""
    id: str
    current_node: str  # current node ID
    target_node: Optional[str] = None
    path: list[str] = Field(default_factory=list)  # ordered node IDs to follow
    path_index: int = 0  # current position in path
    progress: float = 0.0  # [0,1] interpolation between current and next node
    state: AgentState = AgentState.IDLE
    cargo: float = 0.0  # current cargo amount
    max_cargo: float = 100.0
    loading_ticks_remaining: int = 0
    unloading_ticks_remaining: int = 0
    speed: float = 2.0  # units per tick

    class Config:
        use_enum_values = True

    def to_serializable(self) -> dict:
        return {
            "id": self.id,
            "current_node": self.current_node,
            "target_node": self.target_node,
            "path": self.path,
            "path_index": self.path_index,
            "progress": round(self.progress, 3),
            "state": self.state,
            "cargo": round(self.cargo, 1),
            "max_cargo": self.max_cargo,
        }


class Worker(BaseModel):
    """Mine worker assigned to zones."""
    id: str
    current_node: str
    assigned_zone: Optional[str] = None
    path: list[str] = Field(default_factory=list)
    path_index: int = 0
    progress: float = 0.0
    state: AgentState = AgentState.IDLE
    speed: float = 1.0

    class Config:
        use_enum_values = True

    def to_serializable(self) -> dict:
        return {
            "id": self.id,
            "current_node": self.current_node,
            "assigned_zone": self.assigned_zone,
            "path": self.path,
            "path_index": self.path_index,
            "progress": round(self.progress, 3),
            "state": self.state,
        }


class Equipment(BaseModel):
    """Mining equipment (drills, loaders, etc.)."""
    id: str
    equipment_type: EquipmentType
    current_node: str
    assigned_zone: Optional[str] = None
    state: AgentState = AgentState.IDLE
    cooldown_remaining: int = 0  # ticks until available

    class Config:
        use_enum_values = True

    def to_serializable(self) -> dict:
        return {
            "id": self.id,
            "type": self.equipment_type,
            "current_node": self.current_node,
            "assigned_zone": self.assigned_zone,
            "state": self.state,
            "cooldown_remaining": self.cooldown_remaining,
        }
