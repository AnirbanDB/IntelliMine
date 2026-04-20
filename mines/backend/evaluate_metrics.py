#!/usr/bin/env python3
"""
Evaluate IntelliMine metrics via localhost API endpoints.

Metrics covered:
1) A* path cost and runtime
2) CSP feasibility
3) Hazard trends over time
4) Evacuation success rate

Default API base: http://localhost:8000/api

Example:
    python evaluate_metrics.py --duration 45 --path-trials 25 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class PathTrial:
    mode: str
    start: str
    goal: str
    success: bool
    path_cost: float
    runtime_ms: float
    nodes_explored: int


class MineEvaluator:
    def __init__(self, api_base: str, timeout_s: float = 15.0):
        self.api_base = api_base.rstrip("/")
        self.client = httpx.Client(timeout=timeout_s)

    # ---------- HTTP helpers ----------

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.api_base}{path}"

    def get(self, path: str) -> dict[str, Any]:
        r = self.client.get(self._url(path))
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self.client.post(self._url(path), json=body if body is not None else {})
        r.raise_for_status()
        return r.json()

    # ---------- API actions ----------

    def generate_mine(self, seed: int | None = None) -> dict[str, Any]:
        payload = {"seed": seed} if seed is not None else {}
        return self.post("/generate-mine", payload)

    def simulation_action(self, action: str) -> dict[str, Any]:
        return self.post("/run-simulation", {"action": action})

    def update_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return self.post("/update-parameters", {"params": params})

    def get_state(self) -> dict[str, Any]:
        return self.get("/simulation-state")

    def compute_path(self, start: str, goal: str, mode: str) -> tuple[dict[str, Any], float]:
        payload = {
            "start": start,
            "goal": goal,
            "mode": mode,
        }
        t0 = time.perf_counter()
        res = self.post("/compute-path", payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return res, elapsed_ms

    def compute_schedule(self, zones: list[str], num_slots: int) -> dict[str, Any]:
        return self.post("/compute-schedule", {"zones": zones, "num_slots": num_slots})

    # ---------- Metric blocks ----------

    def evaluate_astar(self, graph: dict[str, Any], trials: int, seed: int | None = None) -> dict[str, Any]:
        if seed is not None:
            random.seed(seed)

        nodes = graph.get("nodes", [])
        exits = [n["id"] for n in nodes if n.get("type") == "exit"]
        ores = [n["id"] for n in nodes if n.get("type") == "ore_zone"]
        non_exits = [n["id"] for n in nodes if n.get("type") != "exit"]

        if not exits or not ores:
            raise RuntimeError("Graph must contain at least 1 exit and 1 ore zone.")

        all_trials: list[PathTrial] = []

        modes = ["normal", "hazard", "evacuation"]
        for mode in modes:
            for _ in range(trials):
                if mode == "evacuation":
                    start = random.choice(non_exits or ores)
                    goal = random.choice(exits)
                else:
                    start = random.choice(exits)
                    goal = random.choice(ores)

                res, elapsed_ms = self.compute_path(start, goal, mode)
                all_trials.append(
                    PathTrial(
                        mode=mode,
                        start=start,
                        goal=goal,
                        success=bool(res.get("success", False)),
                        path_cost=float(res.get("total_cost", float("inf"))),
                        runtime_ms=elapsed_ms,
                        nodes_explored=int(res.get("nodes_explored", 0)),
                    )
                )

        summary: dict[str, Any] = {"per_mode": {}, "trials": []}

        for trial in all_trials:
            summary["trials"].append(
                {
                    "mode": trial.mode,
                    "start": trial.start,
                    "goal": trial.goal,
                    "success": trial.success,
                    "path_cost": trial.path_cost,
                    "runtime_ms": round(trial.runtime_ms, 3),
                    "nodes_explored": trial.nodes_explored,
                }
            )

        for mode in modes:
            mode_trials = [t for t in all_trials if t.mode == mode]
            successes = [t for t in mode_trials if t.success]
            runtimes = [t.runtime_ms for t in mode_trials]
            costs = [t.path_cost for t in successes]
            explored = [t.nodes_explored for t in mode_trials]

            summary["per_mode"][mode] = {
                "trial_count": len(mode_trials),
                "success_count": len(successes),
                "success_rate": round(len(successes) / max(1, len(mode_trials)), 4),
                "avg_runtime_ms": round(statistics.mean(runtimes), 3) if runtimes else None,
                "p95_runtime_ms": round(_percentile(runtimes, 95), 3) if runtimes else None,
                "avg_path_cost_success_only": round(statistics.mean(costs), 3) if costs else None,
                "min_path_cost_success_only": round(min(costs), 3) if costs else None,
                "max_path_cost_success_only": round(max(costs), 3) if costs else None,
                "avg_nodes_explored": round(statistics.mean(explored), 3) if explored else None,
            }

        return summary

    def evaluate_csp_feasibility(
        self,
        graph: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        parameters = state.get("parameters", {})
        schedule_params = parameters.get("schedule", {})
        hazard_params = parameters.get("hazard", {})

        capacity = int(schedule_params.get("processing_capacity", 3))
        num_slots = int(schedule_params.get("num_time_slots", 12))
        blast_enabled = bool(schedule_params.get("blast_enabled", True))
        hazard_threshold = float(hazard_params.get("hazard_threshold", 0.6))

        zones = [n["id"] for n in graph.get("nodes", []) if n.get("type") == "ore_zone"]
        hazard_prob = state.get("hazard_probabilities", {})

        schedule_resp = self.compute_schedule(zones=zones, num_slots=num_slots)
        entries: list[dict[str, Any]] = schedule_resp.get("schedule", [])

        adjacency = _zone_adjacency(graph, set(zones))
        violations = _validate_schedule(
            entries=entries,
            adjacency=adjacency,
            capacity=capacity,
            hazard_prob=hazard_prob,
            hazard_threshold=hazard_threshold,
            blast_enabled=blast_enabled,
        )

        non_idle = sum(1 for e in entries if e.get("activity") not in ("idle", "halted"))
        utilization = non_idle / max(1, len(entries))

        return {
            "feasible": len(violations) == 0,
            "violations": violations,
            "violation_count": len(violations),
            "num_entries": len(entries),
            "num_slots": num_slots,
            "num_zones": len(zones),
            "capacity": capacity,
            "blast_enabled": blast_enabled,
            "active_utilization_ratio": round(utilization, 4),
        }

    def evaluate_hazard_and_evacuation(
        self,
        duration_s: float,
        poll_interval_s: float,
    ) -> dict[str, Any]:
        # Encourage enough evacuation events for measurable rate.
        self.update_params(
            {
                "hazard": {
                    "hazard_emerge_chance": 0.08,
                    "hazard_threshold": 0.50,
                    "evacuation_threshold": 0.65,
                }
            }
        )

        self.simulation_action("start")

        snapshots: list[dict[str, Any]] = []
        seen_events: set[tuple[Any, Any, Any]] = set()

        start_t = time.time()
        while time.time() - start_t < duration_s:
            state = self.get_state()
            tick = int(state.get("tick", 0))
            hz = state.get("hazard_probabilities", {})
            active_hazards = len(state.get("active_hazards", []))

            mean_hz = statistics.mean(hz.values()) if hz else 0.0
            max_hz = max(hz.values()) if hz else 0.0

            snapshots.append(
                {
                    "tick": tick,
                    "mean_hazard": round(mean_hz, 6),
                    "max_hazard": round(max_hz, 6),
                    "active_hazards": active_hazards,
                    "hazard_probabilities": hz,
                }
            )

            # Deduplicate log events across rolling windows.
            for ev in state.get("events_log", []):
                key = (ev.get("timestamp"), ev.get("category"), ev.get("message"))
                seen_events.add(key)

            time.sleep(max(0.05, poll_interval_s))

        self.simulation_action("stop")

        means = [s["mean_hazard"] for s in snapshots]
        maxes = [s["max_hazard"] for s in snapshots]
        actives = [s["active_hazards"] for s in snapshots]

        hazard_summary = {
            "samples": len(snapshots),
            "tick_start": snapshots[0]["tick"] if snapshots else None,
            "tick_end": snapshots[-1]["tick"] if snapshots else None,
            "mean_hazard_avg": round(statistics.mean(means), 6) if means else 0.0,
            "mean_hazard_max": round(max(means), 6) if means else 0.0,
            "max_hazard_peak": round(max(maxes), 6) if maxes else 0.0,
            "active_hazards_avg": round(statistics.mean(actives), 4) if actives else 0.0,
            "active_hazards_peak": max(actives) if actives else 0,
            "trend_delta_mean_hazard": round((means[-1] - means[0]), 6) if len(means) > 1 else 0.0,
            "timeseries": snapshots,
        }

        trigger_count = 0
        safe_count = 0
        trapped_count = 0

        for _, category, msg in seen_events:
            text = str(msg).lower()
            cat = str(category).upper()
            if "evacuating from" in text or (cat == "CRITICAL" and "evacuating" in text):
                trigger_count += 1
            if "safely evacuated" in text:
                safe_count += 1
            if "trapped" in text:
                trapped_count += 1

        resolved = safe_count + trapped_count
        success_rate_resolved = (safe_count / resolved) if resolved > 0 else None
        success_rate_triggered = (safe_count / trigger_count) if trigger_count > 0 else None

        evacuation_summary = {
            "evacuation_triggers": trigger_count,
            "safe_evacuations": safe_count,
            "trapped_events": trapped_count,
            "success_rate_resolved": round(success_rate_resolved, 4) if success_rate_resolved is not None else None,
            "success_rate_triggered": round(success_rate_triggered, 4) if success_rate_triggered is not None else None,
        }

        return {
            "hazard_trends": hazard_summary,
            "evacuation": evacuation_summary,
        }

    def close(self):
        self.client.close()


# ---------- Validation helpers ----------

def _zone_adjacency(graph: dict[str, Any], zones: set[str]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {z: set() for z in zones}
    for e in graph.get("edges", []):
        s, t = e.get("source"), e.get("target")
        if s in zones and t in zones:
            adj[s].add(t)
            adj[t].add(s)
    return adj


def _validate_schedule(
    entries: list[dict[str, Any]],
    adjacency: dict[str, set[str]],
    capacity: int,
    hazard_prob: dict[str, float],
    hazard_threshold: float,
    blast_enabled: bool,
) -> list[str]:
    violations: list[str] = []

    assignment: dict[tuple[str, int], str] = {}
    by_slot: dict[int, list[tuple[str, str]]] = {}

    for e in entries:
        z = e.get("zone_id")
        t = int(e.get("time_slot"))
        a = str(e.get("activity"))
        assignment[(z, t)] = a
        by_slot.setdefault(t, []).append((z, a))

        if not blast_enabled and a == "blast":
            violations.append(f"blast_disabled_violation: zone={z}, slot={t}")

        hp = float(hazard_prob.get(z, 0.0))
        if hp >= hazard_threshold and a != "halted":
            violations.append(f"hazard_halt_violation: zone={z}, slot={t}, hp={hp:.3f}, activity={a}")

    # Capacity check
    for slot, vals in by_slot.items():
        active = sum(1 for _, a in vals if a not in ("idle", "halted"))
        if active > capacity:
            violations.append(f"capacity_violation: slot={slot}, active={active}, capacity={capacity}")

    # Blast adjacency and cooldown checks
    for (z, t), a in assignment.items():
        if a != "blast":
            continue

        # adjacent zones same slot cannot blast
        for nb in adjacency.get(z, set()):
            if assignment.get((nb, t)) == "blast":
                violations.append(f"adjacent_blast_violation: zones=({z},{nb}), slot={t}")

        # same zone consecutive slots cannot blast
        if assignment.get((z, t - 1)) == "blast" or assignment.get((z, t + 1)) == "blast":
            violations.append(f"cooldown_violation: zone={z}, around_slot={t}")

    # Deduplicate while preserving order
    seen = set()
    out = []
    for v in violations:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    k = (len(vs) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(vs) - 1)
    if f == c:
        return vs[f]
    return vs[f] + (vs[c] - vs[f]) * (k - f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate IntelliMine metrics from localhost API")
    parser.add_argument("--api-base", default="http://localhost:8000/api", help="API base URL")
    parser.add_argument("--seed", type=int, default=42, help="Mine generation seed")
    parser.add_argument("--path-trials", type=int, default=20, help="Trials per A* mode")
    parser.add_argument("--duration", type=float, default=30.0, help="Hazard/evacuation observation duration (s)")
    parser.add_argument("--poll-interval", type=float, default=0.5, help="State polling interval in seconds")
    parser.add_argument("--output", default="metrics_report.json", help="Output JSON file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    evaluator = MineEvaluator(api_base=args.api_base)
    out_path = Path(args.output)

    try:
        print(f"[1/5] Generating mine (seed={args.seed})...")
        graph = evaluator.generate_mine(seed=args.seed)

        print("[2/5] Fetching initial simulation state...")
        state = evaluator.get_state()

        print(f"[3/5] Running A* benchmarks ({args.path_trials} trials/mode)...")
        astar_metrics = evaluator.evaluate_astar(graph=graph, trials=args.path_trials, seed=args.seed)

        print("[4/5] Evaluating CSP feasibility...")
        csp_metrics = evaluator.evaluate_csp_feasibility(graph=graph, state=state)

        print(f"[5/5] Tracking hazard trends + evacuation ({args.duration:.1f}s)...")
        haz_evac_metrics = evaluator.evaluate_hazard_and_evacuation(
            duration_s=args.duration,
            poll_interval_s=args.poll_interval,
        )

        report = {
            "meta": {
                "api_base": args.api_base,
                "seed": args.seed,
                "path_trials_per_mode": args.path_trials,
                "duration_s": args.duration,
                "poll_interval_s": args.poll_interval,
                "generated_at_epoch": time.time(),
            },
            "astar": astar_metrics,
            "csp": csp_metrics,
            "hazard_and_evacuation": haz_evac_metrics,
        }

        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        # Console summary
        print("\n=== METRICS SUMMARY ===")
        print("A*:")
        for mode, m in report["astar"]["per_mode"].items():
            print(
                f"  - {mode:<10} "
                f"success={m['success_count']}/{m['trial_count']} "
                f"avg_runtime={m['avg_runtime_ms']} ms "
                f"avg_cost={m['avg_path_cost_success_only']}"
            )

        csp = report["csp"]
        print(
            f"CSP: feasible={csp['feasible']} violations={csp['violation_count']} "
            f"utilization={csp['active_utilization_ratio']}"
        )

        hz = report["hazard_and_evacuation"]["hazard_trends"]
        ev = report["hazard_and_evacuation"]["evacuation"]
        print(
            f"Hazard: samples={hz['samples']} mean_avg={hz['mean_hazard_avg']} "
            f"peak_max={hz['max_hazard_peak']} active_peak={hz['active_hazards_peak']}"
        )
        print(
            f"Evacuation: triggers={ev['evacuation_triggers']} safe={ev['safe_evacuations']} "
            f"trapped={ev['trapped_events']} success_resolved={ev['success_rate_resolved']}"
        )

        print(f"\nSaved report to: {out_path.resolve()}")
        return 0

    except httpx.HTTPStatusError as e:
        print("HTTP error:", e)
        if e.response is not None:
            print("Response:", e.response.text)
        return 2
    except Exception as e:
        print("Evaluation failed:", e)
        return 1
    finally:
        evaluator.close()


if __name__ == "__main__":
    raise SystemExit(main())
