"""
Simulation Engine

Central orchestrator: tick-based, event-driven, ties together
A*, CSP scheduling, and Bayesian hazard reasoning.
"""
import random
import time
from typing import Dict, Any

from models.simulation_state import SimulationState, SimulationStatus, PathResult, ScheduleEntry
from models.mine_graph import NodeType
from models.agents import Truck, Worker, AgentState
from models.hazards import HazardEvent, SensorReading, HazardType
from config import config

from engine.graph_engine import generate_mine
from engine.event_manager import EventManager
from algorithms.astar import astar_search, find_evacuation_path
from algorithms.csp import compute_schedule
from algorithms.bayesian import update_mine_hazard_states


class SimulationEngine:
    def __init__(self):
        self.state = SimulationState()
        self.state.parameters = config.model_dump()
        self.event_manager = EventManager()

        self._truck_map: Dict[str, Truck] = {}
        self._worker_map: Dict[str, Worker] = {}

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def initialize(self, seed: int = None):
        """Reset and build a fresh mine simulation."""
        mine_p = self.state.parameters.get("mine", config.mine.model_dump())
        self.state.graph = generate_mine(
            num_junctions=mine_p.get("num_junctions"),
            num_ore_zones=mine_p.get("num_ore_zones"),
            num_exits=mine_p.get("num_exits"),
            connectivity=mine_p.get("connectivity"),
            seed=seed,
        )
        self.state.tick = 0
        self.state.status = SimulationStatus.STOPPED
        self.state.trucks = []
        self.state.workers = []
        self.state.equipment = []
        self.state.active_hazards = []
        self.state.sensor_readings = {}
        self.state.hazard_probabilities = {}
        self.state.schedule = []
        self.state.paths = []
        self.state.events_log = []
        self.event_manager.clear()

        self._spawn_agents()
        self._initialize_sensors()
        self._update_algorithms()
        self._log("SYSTEM", "Mine initialized.")

    def start(self):
        if not self.state.graph:
            self.initialize()
        self.state.status = SimulationStatus.RUNNING
        self._log("SYSTEM", "Simulation started.")

    def pause(self):
        self.state.status = SimulationStatus.PAUSED
        self._log("SYSTEM", "Simulation paused.")

    def stop(self):
        self.state.status = SimulationStatus.STOPPED
        self._log("SYSTEM", "Simulation stopped.")

    def update_parameters(self, new_params: Dict[str, Any]):
        """
        Deep-merge new_params into state.parameters.
        Keys that map to dicts are merged; scalars are replaced.
        Changing mine-topology params triggers a full re-init.
        """
        mine_keys_changed = False
        for section, values in new_params.items():
            if section not in self.state.parameters:
                self.state.parameters[section] = {}
            if isinstance(values, dict):
                self.state.parameters[section].update(values)
            else:
                self.state.parameters[section] = values
            if section == "mine":
                mine_keys_changed = True

        self._log("SYSTEM", "Parameters updated.")

        if mine_keys_changed:
            # Preserve status, regenerate topology
            prev_status = self.state.status
            self.initialize()
            if prev_status == SimulationStatus.RUNNING:
                self.start()
        else:
            # Just recompute algorithms with the new settings
            self._respawn_agents_if_needed(new_params)
            self._update_algorithms()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _respawn_agents_if_needed(self, changed: Dict[str, Any]):
        """Re-spawn trucks/workers when counts change."""
        sim_section = changed.get("simulation", {})
        if "num_trucks" in sim_section or "num_workers" in sim_section:
            self._spawn_agents()

    def _spawn_agents(self):
        sim_p = self.state.parameters.get("simulation", config.simulation.model_dump())
        exits = self.state.graph.get_exit_nodes()
        ore_zones = self.state.graph.get_ore_zones()

        if not exits or not ore_zones:
            self._log("ERROR", "Cannot spawn agents: missing exits or ore zones.")
            return

        self._truck_map = {}
        self.state.trucks = []
        for i in range(sim_p.get("num_trucks", 3)):
            start = random.choice(exits).id
            truck = Truck(
                id=f"truck_{i}",
                current_node=start,
                speed=sim_p.get("truck_speed", 2.0),
            )
            self.state.trucks.append(truck)
            self._truck_map[truck.id] = truck

        self._worker_map = {}
        self.state.workers = []
        for i in range(sim_p.get("num_workers", 8)):
            start = random.choice(ore_zones).id
            worker = Worker(
                id=f"worker_{i}",
                current_node=start,
                assigned_zone=start,
                speed=sim_p.get("worker_speed", 1.0),
            )
            self.state.workers.append(worker)
            self._worker_map[worker.id] = worker

    def _initialize_sensors(self):
        haz_p = self.state.parameters.get("hazard", config.hazard.model_dump())
        for node in self.state.graph.nodes.values():
            self.state.sensor_readings[node.id] = SensorReading(
                node_id=node.id,
                gas_level=max(0.0, min(1.0,
                    haz_p.get("gas_level_default", 0.2) + random.uniform(-0.05, 0.05)
                )),
                vibration=max(0.0, min(1.0,
                    haz_p.get("vibration_default", 0.1) + random.uniform(-0.02, 0.05)
                )),
                blast_activity=haz_p.get("blast_activity_default", 0.0),
                moisture=haz_p.get("moisture_default", 0.3),
            )

    def _log(self, category: str, message: str):
        self.state.events_log.append({
            "tick": self.state.tick,
            "category": category,
            "message": message,
            "timestamp": time.time(),
        })
        if len(self.state.events_log) > 120:
            self.state.events_log = self.state.events_log[-100:]

    # ── Algorithm pipeline ─────────────────────────────────────────────────────

    def _update_algorithms(self):
        """Recompute hazard probabilities, schedule, and truck paths."""
        if not self.state.graph:
            return

        haz_p = self.state.parameters.get("hazard", config.hazard.model_dump())
        sched_p = self.state.parameters.get("schedule", config.schedule.model_dump())

        # 1. Bayesian hazard update
        self.state.hazard_probabilities = update_mine_hazard_states(
            list(self.state.graph.nodes.values()),
            self.state.sensor_readings,
        )

        # 2. Propagate probabilities back onto node objects & emit hazard events
        hazard_thresh = haz_p.get("hazard_threshold", 0.6)
        for node_id, prob in self.state.hazard_probabilities.items():
            node = self.state.graph.get_node(node_id)
            if not node:
                continue
            node.hazard_probability = prob
            if prob > hazard_thresh:
                already_active = any(
                    h.node_id == node_id and h.is_active
                    for h in self.state.active_hazards
                )
                if not already_active:
                    h_type = (
                        HazardType.COLLAPSE
                        if self.state.sensor_readings.get(node_id, SensorReading(node_id=node_id)).vibration > 0.5
                        else HazardType.GAS_LEAK
                    )
                    self.state.active_hazards.append(HazardEvent(
                        id=f"haz_{self.state.tick}_{node_id}",
                        hazard_type=h_type,
                        node_id=node_id,
                        severity=prob,
                        tick_started=self.state.tick,
                    ))
                    self._log("HAZARD", f"Hazard emerged at {node.label} (P={prob:.2f})")

        # 3. Expire old hazard events
        self.state.active_hazards = [
            h for h in self.state.active_hazards
            if self.state.tick - h.tick_started < h.duration_ticks
        ]

        # 4. CSP schedule
        ore_zones = [z.id for z in self.state.graph.get_ore_zones()]
        raw_schedule = compute_schedule(
            self.state.graph,
            ore_zones,
            sched_p.get("num_time_slots", 12),
            self.state.hazard_probabilities,
            blast_enabled=sched_p.get("blast_enabled", True),
        )
        self.state.schedule = [
            ScheduleEntry(
                zone_id=s["zone_id"],
                time_slot=s["time_slot"],
                activity=s["activity"],
                equipment_id=s.get("equipment_id"),
            )
            for s in raw_schedule
        ]

        # 5. Route trucks via A*
        self._plan_truck_paths()

    def _plan_truck_paths(self):
        if not self.state.graph:
            return

        haz_p = self.state.parameters.get("hazard", config.hazard.model_dump())
        exits = self.state.graph.get_exit_nodes()
        ore_zones = self.state.graph.get_ore_zones()
        if not exits or not ore_zones:
            return

        self.state.paths = []

        # Always re-emit paths for MOVING trucks so the frontend can render them
        for truck in self.state.trucks:
            if truck.state == AgentState.MOVING and truck.path:
                self.state.paths.append(PathResult(
                    agent_id=truck.id,
                    path=truck.path,
                    total_cost=0.0,
                    mode="hazard",
                ))

        for truck in self.state.trucks:
            if truck.state not in (AgentState.IDLE, AgentState.WAITING):
                continue

            node_obj = self.state.graph.get_node(truck.current_node)
            if node_obj and node_obj.node_type == NodeType.EXIT:
                target = random.choice(ore_zones).id
            else:
                target = random.choice(exits).id

            truck.target_node = target
            result = astar_search(
                self.state.graph,
                truck.current_node,
                target,
                mode="hazard",
                hazard_lambda=haz_p.get("hazard_lambda", 2.0),
                hazard_threshold=haz_p.get("hazard_threshold", 0.6),
            )

            if result.success:
                truck.path = result.path
                truck.path_index = 0
                truck.progress = 0.0
                truck.state = AgentState.MOVING
                self.state.paths.append(PathResult(
                    agent_id=truck.id,
                    path=result.path,
                    total_cost=result.total_cost,
                    mode=result.mode,
                ))
            else:
                self._log("WARNING", f"No path found for {truck.id} → {target}")

    # ── Tick ───────────────────────────────────────────────────────────────────

    def tick(self):
        """Execute one simulation step."""
        if self.state.status != SimulationStatus.RUNNING:
            return

        self.state.tick += 1
        self.event_manager.process_events(self.state.tick)

        self._evolve_sensors()

        # Full algorithm recompute every 5 ticks (or when hazard threshold just crossed)
        if self.state.tick % 5 == 0:
            self._update_algorithms()

        self._step_agents()

    def _evolve_sensors(self):
        """Apply random drift and blast-schedule influence to sensor readings."""
        haz_p = self.state.parameters.get("hazard", config.hazard.model_dump())
        sched_p = self.state.parameters.get("schedule", config.schedule.model_dump())

        current_slot = self.state.tick % max(1, sched_p.get("num_time_slots", 12))
        active_blast_zones = {
            s.zone_id
            for s in self.state.schedule
            if s.time_slot == current_slot and s.activity == "blast"
        }

        # Random spontaneous hazard spikes (rare)
        emerge_chance = haz_p.get("hazard_emerge_chance", 0.03)

        for node_id, sensor in self.state.sensor_readings.items():
            # Random drift (small)
            if random.random() < 0.15:
                sensor.gas_level = max(0.0, min(1.0,
                    sensor.gas_level + random.uniform(-0.04, 0.04)
                ))
            if random.random() < 0.10:
                sensor.vibration = max(0.0, min(1.0,
                    sensor.vibration + random.uniform(-0.03, 0.03)
                ))

            # Blast activity drives up gas + vibration
            if node_id in active_blast_zones:
                sensor.blast_activity = min(1.0, sensor.blast_activity + 0.4)
                sensor.vibration = min(1.0, sensor.vibration + 0.3)
                sensor.gas_level = min(1.0, sensor.gas_level + 0.1)
            else:
                sensor.blast_activity = max(0.0, sensor.blast_activity - 0.15)
                sensor.vibration = max(
                    haz_p.get("vibration_default", 0.1),
                    sensor.vibration - 0.05,
                )

            # Spontaneous hazard spike
            if random.random() < emerge_chance:
                sensor.gas_level = min(1.0, sensor.gas_level + random.uniform(0.2, 0.4))
                sensor.vibration = min(1.0, sensor.vibration + random.uniform(0.1, 0.3))
                self._log("WARNING", f"Sensor spike at node {node_id}")

            # Natural recovery toward baseline
            baseline_gas = haz_p.get("gas_level_default", 0.2)
            if sensor.gas_level > baseline_gas + 0.1:
                sensor.gas_level = max(baseline_gas, sensor.gas_level - 0.02)

    # ── Agent stepping ─────────────────────────────────────────────────────────

    def _step_agents(self):
        sim_p = self.state.parameters.get("simulation", config.simulation.model_dump())
        haz_p = self.state.parameters.get("hazard", config.hazard.model_dump())
        evac_thresh = haz_p.get("evacuation_threshold", 0.8)

        for truck in self.state.trucks:
            self._step_truck(truck, sim_p)

        for worker in self.state.workers:
            self._step_worker(worker, evac_thresh)

        # Append evacuating worker paths so frontend renders them
        for worker in self.state.workers:
            if worker.state == AgentState.EVACUATING and worker.path:
                # Avoid duplicates (worker path already added on trigger)
                if not any(p.agent_id == worker.id for p in self.state.paths):
                    self.state.paths.append(PathResult(
                        agent_id=worker.id,
                        path=worker.path,
                        total_cost=0.0,
                        mode="evacuation",
                    ))

    def _step_truck(self, truck: Truck, sim_p: dict):
        if truck.state == AgentState.MOVING:
            if not truck.path or truck.path_index >= len(truck.path) - 1:
                truck.state = AgentState.IDLE
                return

            next_node_id = truck.path[truck.path_index + 1]
            next_node = self.state.graph.get_node(next_node_id)

            # Re-route if next node became dangerous
            if next_node and next_node.hazard_probability > 0.85:
                self._log("WARNING", f"{truck.id} re-routing — hazard at {next_node.label}")
                truck.state = AgentState.WAITING
                return

            cur_node = self.state.graph.get_node(truck.path[truck.path_index])
            if cur_node and next_node:
                dist = max(cur_node.distance_to(next_node), 0.1)
                truck.progress += truck.speed / dist
                if truck.progress >= 1.0:
                    truck.path_index += 1
                    truck.progress = 0.0
                    truck.current_node = next_node_id
                    if truck.path_index >= len(truck.path) - 1:
                        dest = self.state.graph.get_node(truck.current_node)
                        if dest and dest.node_type == NodeType.ORE_ZONE:
                            truck.state = AgentState.LOADING
                            truck.loading_ticks_remaining = sim_p.get("loading_ticks", 3)
                        else:
                            truck.state = AgentState.UNLOADING
                            truck.unloading_ticks_remaining = sim_p.get("unloading_ticks", 2)

        elif truck.state == AgentState.LOADING:
            truck.loading_ticks_remaining -= 1
            if truck.loading_ticks_remaining <= 0:
                truck.cargo = truck.max_cargo
                truck.state = AgentState.IDLE
                self._log("INFO", f"{truck.id} loaded at {truck.current_node}")

        elif truck.state == AgentState.UNLOADING:
            truck.unloading_ticks_remaining -= 1
            if truck.unloading_ticks_remaining <= 0:
                truck.cargo = 0.0
                truck.state = AgentState.IDLE
                self._log("INFO", f"{truck.id} unloaded at {truck.current_node}")

    def _step_worker(self, worker: Worker, evac_thresh: float):
        node = self.state.graph.get_node(worker.current_node)

        # Check if current node just became dangerous → begin evacuation
        if (
            node
            and node.hazard_probability > evac_thresh
            and worker.state != AgentState.EVACUATING
        ):
            self._log("CRITICAL", f"{worker.id} evacuating from {node.label}!")
            worker.state = AgentState.EVACUATING
            res = find_evacuation_path(self.state.graph, worker.current_node)
            if res.success:
                worker.path = res.path
                worker.path_index = 0
                worker.progress = 0.0
                self.state.paths.append(PathResult(
                    agent_id=worker.id,
                    path=res.path,
                    total_cost=res.total_cost,
                    mode="evacuation",
                ))
            else:
                self._log("CRITICAL", f"{worker.id} TRAPPED at {node.label} — no exit path!")

        if worker.state == AgentState.EVACUATING:
            if not worker.path or worker.path_index >= len(worker.path) - 1:
                # Reached (or path exhausted)
                dest = self.state.graph.get_node(worker.current_node)
                if dest and dest.node_type == NodeType.EXIT:
                    worker.state = AgentState.IDLE
                    self._log("SYSTEM", f"{worker.id} safely evacuated.")
                return

            cur_node = self.state.graph.get_node(worker.path[worker.path_index])
            nxt_node = self.state.graph.get_node(worker.path[worker.path_index + 1])
            if cur_node and nxt_node:
                dist = max(cur_node.distance_to(nxt_node), 0.1)
                worker.progress += worker.speed / dist
                if worker.progress >= 1.0:
                    worker.path_index += 1
                    worker.progress = 0.0
                    worker.current_node = nxt_node.id
