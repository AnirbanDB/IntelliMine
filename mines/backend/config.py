"""
IntelliMine — Global Configuration
"""
from pydantic import BaseModel


class MineConfig(BaseModel):
    """Default mine generation parameters."""
    num_junctions: int = 15
    num_ore_zones: int = 6
    num_exits: int = 3
    min_edge_distance: float = 20.0
    max_edge_distance: float = 100.0
    connectivity: float = 0.35  # probability of edge between nearby nodes


class SimulationConfig(BaseModel):
    """Simulation engine parameters."""
    tick_rate_ms: int = 200  # milliseconds per tick
    num_trucks: int = 3
    num_workers: int = 8
    num_equipment: int = 4
    truck_speed: float = 12.0  # units per tick (6x faster)
    worker_speed: float = 4.0
    loading_ticks: int = 3
    unloading_ticks: int = 2


class HazardConfig(BaseModel):
    """Hazard / Bayesian parameters."""
    hazard_threshold: float = 0.6  # probability above which hazard triggers
    evacuation_threshold: float = 0.8  # immediate evacuation
    hazard_lambda: float = 2.0  # weight for hazard-aware A*
    gas_level_default: float = 0.2
    vibration_default: float = 0.1
    blast_activity_default: float = 0.0
    moisture_default: float = 0.3
    hazard_emerge_chance: float = 0.03  # per tick per node
    hazard_duration_ticks: int = 15


class ScheduleConfig(BaseModel):
    """CSP scheduling parameters."""
    num_time_slots: int = 12
    processing_capacity: int = 3  # max simultaneous active zones
    blast_cooldown_slots: int = 2  # slots between blasts in same zone
    shift_duration_slots: int = 12
    blast_enabled: bool = True     # if False, blast removed from CSP domains


class AppConfig(BaseModel):
    """Top-level application configuration."""
    mine: MineConfig = MineConfig()
    simulation: SimulationConfig = SimulationConfig()
    hazard: HazardConfig = HazardConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    websocket_broadcast_interval_ms: int = 500
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


# Global singleton
config = AppConfig()
