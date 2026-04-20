"""
Hazard event and sensor models.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HazardType(str, Enum):
    GAS_LEAK = "gas_leak"
    COLLAPSE = "collapse"
    TOXIC = "toxic"
    FIRE = "fire"
    FLOOD = "flood"


class HazardEvent(BaseModel):
    """A discrete hazard event in the simulation."""
    id: str
    hazard_type: HazardType
    node_id: str  # affected node
    severity: float = 0.5  # [0, 1]
    tick_started: int = 0
    duration_ticks: int = 15
    is_active: bool = True

    class Config:
        use_enum_values = True

    @property
    def ticks_remaining(self) -> int:
        return max(0, self.duration_ticks)

    def to_serializable(self) -> dict:
        return {
            "id": self.id,
            "type": self.hazard_type,
            "node_id": self.node_id,
            "severity": round(self.severity, 3),
            "tick_started": self.tick_started,
            "duration_ticks": self.duration_ticks,
            "is_active": self.is_active,
        }


class SensorReading(BaseModel):
    """Sensor readings for a mine node (inputs to Bayesian net)."""
    node_id: str
    gas_level: float = 0.2      # [0, 1]
    vibration: float = 0.1      # [0, 1]
    blast_activity: float = 0.0  # [0, 1]
    moisture: float = 0.3       # [0, 1]
    temperature: float = 0.3    # [0, 1] normalized

    def to_evidence_dict(self) -> dict[str, float]:
        return {
            "gas_level": self.gas_level,
            "vibration": self.vibration,
            "blast_activity": self.blast_activity,
            "moisture": self.moisture,
        }

    def to_serializable(self) -> dict:
        return {
            "node_id": self.node_id,
            "gas_level": round(self.gas_level, 3),
            "vibration": round(self.vibration, 3),
            "blast_activity": round(self.blast_activity, 3),
            "moisture": round(self.moisture, 3),
            "temperature": round(self.temperature, 3),
        }
