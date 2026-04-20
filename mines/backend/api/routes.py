"""
REST Endpoints
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from engine.simulation import SimulationEngine
from algorithms.astar import astar_search, find_evacuation_path
from algorithms.csp import compute_schedule
from algorithms.bayesian import compute_hazard_probabilities

router = APIRouter()


def get_engine() -> SimulationEngine:
    from main import engine  # late import to avoid circular dep
    return engine


# ── Request Bodies ──────────────────────────────────────────────────────────────

class GenerateMineRequest(BaseModel):
    seed: Optional[int] = None


class SimulationActionRequest(BaseModel):
    action: Optional[str] = "start"  # "start" | "pause" | "stop" (aliases supported)


class ConfigUpdate(BaseModel):
    params: Dict[str, Any]


class ComputePathRequest(BaseModel):
    start: str
    goal: str
    mode: str = "hazard"
    hazard_lambda: float = 2.0
    hazard_threshold: float = 0.6


class ComputeScheduleRequest(BaseModel):
    zones: Optional[List[str]] = None
    num_slots: int = 12


class ComputeHazardRequest(BaseModel):
    evidence: Dict[str, float]


class SolvePathRequest(BaseModel):
    """Game-mode: compare a player-supplied path against the optimal A* path."""
    start: str
    goal: str
    player_path: List[str]  # ordered node IDs chosen by the player


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.post("/generate-mine")
async def api_generate_mine(
    body: GenerateMineRequest = GenerateMineRequest(),
    engine: SimulationEngine = Depends(get_engine),
):
    engine.initialize(seed=body.seed)
    return engine.state.graph.to_serializable()


@router.post("/run-simulation")
async def api_run_simulation(
    body: SimulationActionRequest = SimulationActionRequest(),
    engine: SimulationEngine = Depends(get_engine),
):
    raw_action = (body.action or "start").strip().lower()
    action_aliases = {
        "resume": "start",
        "run": "start",
        "play": "start",
    }
    action = action_aliases.get(raw_action, raw_action)

    if action == "start":
        engine.start()
    elif action == "pause":
        engine.pause()
    elif action == "stop":
        engine.stop()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {body.action}. Use one of: start, pause, stop.",
        )
    return {"status": engine.state.status.value}


@router.post("/update-parameters")
async def api_update_parameters(
    update: ConfigUpdate,
    engine: SimulationEngine = Depends(get_engine),
):
    engine.update_parameters(update.params)
    return {"message": "Parameters updated", "parameters": engine.state.parameters}


@router.get("/simulation-state")
async def api_get_state(engine: SimulationEngine = Depends(get_engine)):
    return engine.state.to_serializable()


@router.post("/compute-path")
async def api_compute_path(
    body: ComputePathRequest,
    engine: SimulationEngine = Depends(get_engine),
):
    """Run A* on the current mine graph."""
    if not engine.state.graph:
        raise HTTPException(status_code=400, detail="Mine not initialized")

    if body.mode == "evacuation":
        result = find_evacuation_path(
            engine.state.graph, body.start,
            hazard_lambda=body.hazard_lambda,
            hazard_threshold=body.hazard_threshold,
        )
    else:
        result = astar_search(
            engine.state.graph, body.start, body.goal,
            mode=body.mode,
            hazard_lambda=body.hazard_lambda,
            hazard_threshold=body.hazard_threshold,
        )

    return {
        "path": result.path,
        "total_cost": result.total_cost,
        "nodes_explored": result.nodes_explored,
        "success": result.success,
        "mode": result.mode,
        "fallback_node": result.fallback_node,
    }


@router.post("/compute-schedule")
async def api_compute_schedule(
    body: ComputeScheduleRequest,
    engine: SimulationEngine = Depends(get_engine),
):
    if not engine.state.graph:
        raise HTTPException(status_code=400, detail="Mine not initialized")

    zones = body.zones or [z.id for z in engine.state.graph.get_ore_zones()]
    sched_p = engine.state.parameters.get("schedule", {})
    schedule = compute_schedule(
        engine.state.graph, zones, body.num_slots,
        engine.state.hazard_probabilities,
        blast_enabled=sched_p.get("blast_enabled", True),
    )
    return {"schedule": schedule, "zones": zones, "num_slots": body.num_slots}


@router.post("/compute-hazard")
async def api_compute_hazard(body: ComputeHazardRequest):
    return compute_hazard_probabilities(body.evidence)


@router.get("/mine-graph")
async def api_get_graph(engine: SimulationEngine = Depends(get_engine)):
    if not engine.state.graph:
        raise HTTPException(status_code=400, detail="Mine not initialized")
    return engine.state.graph.to_serializable()


@router.post("/solve-path")
async def api_solve_path(
    body: SolvePathRequest,
    engine: SimulationEngine = Depends(get_engine),
):
    """
    Game mode: evaluate the player's chosen path vs the optimal A* path.
    Returns scoring info, the optimal path, and per-edge cost breakdown.
    """
    if not engine.state.graph:
        raise HTTPException(status_code=400, detail="Mine not initialized")

    graph = engine.state.graph

    # Validate player path: all nodes must exist and be adjacent
    def path_cost(path: List[str]) -> float:
        total = 0.0
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            edges = [e for e in graph.edges.get(src, []) if e.target == tgt]
            if not edges:
                return float("inf")
            total += min(e.weight for e in edges)
        return round(total, 2)

    def path_edge_details(path: List[str]):
        details = []
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            edges = [e for e in graph.edges.get(src, []) if e.target == tgt]
            if edges:
                e = min(edges, key=lambda x: x.weight)
                details.append({
                    "from": src, "to": tgt,
                    "distance": round(e.distance, 1),
                    "gradient": round(e.gradient, 2),
                    "condition": round(e.condition_factor, 2),
                    "cost": round(e.weight, 2),
                })
            else:
                details.append({"from": src, "to": tgt, "cost": None, "invalid": True})
        return details

    # Compute optimal A* path (no-blast, normal routing mode)
    optimal = astar_search(graph, body.start, body.goal, mode="normal")

    player_cost  = path_cost(body.player_path)
    optimal_cost = optimal.total_cost if optimal.success else float("inf")

    # Score: 100 if perfect, scaled down by cost ratio
    if player_cost == float("inf"):
        score = 0
        verdict = "INVALID"
    elif optimal_cost == 0 or optimal_cost == float("inf"):
        score = 100
        verdict = "OPTIMAL"
    else:
        ratio = optimal_cost / player_cost  # ≤ 1.0 (player >= optimal)
        score = max(0, round(ratio * 100))
        if score >= 99:
            verdict = "OPTIMAL"
        elif score >= 80:
            verdict = "GREAT"
        elif score >= 60:
            verdict = "GOOD"
        elif score >= 40:
            verdict = "POOR"
        else:
            verdict = "TERRIBLE"

    return {
        "player_path":    body.player_path,
        "player_cost":    player_cost,
        "player_edges":   path_edge_details(body.player_path),
        "optimal_path":   optimal.path,
        "optimal_cost":   optimal_cost,
        "optimal_edges":  path_edge_details(optimal.path),
        "score":          score,
        "verdict":        verdict,
        "nodes_explored": optimal.nodes_explored,
    }
