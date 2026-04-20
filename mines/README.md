# IntelliMine — AI-Driven Mine Operations Simulator

An underground mine simulator with real pathfinding, constraint scheduling, and probabilistic hazard reasoning. Built to make the algorithms visible and interactive.

---

## How the Algorithms Work

### A* Search — Hazard-Aware Pathfinding

A* finds the lowest-cost route through the mine tunnel network. Each tunnel (edge) has three physical properties:

- **distance** — physical length of the tunnel
- **gradient** — steepness (harder to traverse uphill)
- **condition_factor** — tunnel wear/damage (1.0 = perfect, 0.0 = impassable)

The edge traversal cost is:

```
weight = distance × gradient × condition_factor
```

The heuristic combines Euclidean distance with a hazard penalty:

```
h(n) = euclidean_distance(n, goal) + λ × P(hazard at n)
```

This makes A* route around high-hazard zones rather than through them. Higher `λ` (hazard_lambda) = more aggressive hazard avoidance.

**Three routing modes:**
- `normal` — pure physical cost, no hazard weighting
- `hazard` — composite cost with hazard heuristic bias
- `evacuation` — tries all exits, returns the cheapest escape route; if all paths are blocked by hazard, falls back to the nearest safe node

**Game Mode** lets you draw your own path through the mine before seeing the A* solution. Your path is scored against the optimal cost (0–100). The backend runs A* on `normal` mode (no blast restrictions) and returns per-edge cost breakdowns for both paths side by side.

---

### CSP Solver — Operation Scheduling with AC-3

Scheduling mine operations is a Constraint Satisfaction Problem. The solver assigns an activity to each (zone, time_slot) pair.

**Variables:** `(zone_id, time_slot)` — one per ore zone per scheduling slot

**Domains:** `["blast", "drill", "load", "idle"]`
- Domain collapses to `["halted"]` when a zone's hazard probability exceeds the threshold
- When blast mode is disabled, `"blast"` is removed from all domains

**Constraints enforced:**

| Constraint | Rule |
|---|---|
| Adjacency | No two adjacent zones may both blast in the same time slot |
| Cooldown | A zone cannot blast in two consecutive time slots |
| Capacity | At most N zones may be actively working in any one slot |
| Hazard | Zones above the hazard threshold are forced to "halted" |

**AC-3 (Arc Consistency 3)** runs before backtracking. It propagates constraint implications through all variable pairs:

1. Builds an arc queue over all pairs `(Xi, Xj)` with binary constraints between them (adjacency arcs for same-slot zone pairs, cooldown arcs for same-zone consecutive-slot pairs)
2. For each arc `(Xi, Xj)`, calls `_revise()` to remove any value from `domains[Xi]` that has no consistent support in `domains[Xj]`
3. If a domain shrinks, re-adds all arcs pointing into that variable
4. Returns `False` (unsatisfiable) if any domain becomes empty

After AC-3, backtracking search assigns values with:
- **MRV (Minimum Remaining Values)** — always pick the variable with the smallest domain next (most constrained first)
- **LCV (Least Constraining Value)** — try values that eliminate fewest options from neighbours first
- **Forward checking** — after each assignment, prune "blast" from adjacent zones' same-slot domains and from the same zone's neighbouring time slots; undo on backtrack

If the full solver returns `None` (unsatisfiable), it falls back to all-idle/all-halted.

The Gantt chart in the UI shows the solver's output: 💥 blast · ⛏ drill · 📦 load · · idle · ⛔ halted

---

### Bayesian Network — Probabilistic Hazard Reasoning

Each mine node is assigned a hazard probability via a three-node Bayesian Network:

```
  [GasLevel]  [BlastActivity]       [Vibration]  [MoistureLevel]
       \           /                      \           /
     [ToxicHazard]                    [CollapseRisk]
            \                              /
                    [OverallHazard]
```

**ToxicHazard** — high gas + blast activity increases toxic risk (noisy-OR):
```
P(Toxic=1 | gas, blast) = 1 - (1-0.8)^gas × (1-0.6)^blast
```

**CollapseRisk** — vibration + moisture increases structural risk:
```
P(Collapse=1 | vib, moisture) = 1 - (1-0.7)^vib × (1-0.5)^moisture
```

**OverallHazard** — combination of both parent risks:
```
P(Overall=1 | toxic, collapse) = 1 - (1-0.9)^toxic × (1-0.85)^collapse
```

Sensor readings (gas_level, blast_activity, vibration, moisture) are read from each zone's sensors at each tick and passed as evidence. The resulting `OverallHazard` probability drives:

- The A* heuristic penalty `λ × P(hazard)`
- The CSP domain collapse (zone forced to "halted" above threshold)
- Visual pulse animations and the hazard dashboard

---

## Architecture

```
backend/
  main.py               FastAPI app + WebSocket broadcast loop
  config.py             All tunable parameters (speeds, thresholds, capacities)
  engine/
    simulation.py       Tick engine: sensor evolution, agent movement, scheduling
    graph_engine.py     Procedural mine generation (layered hierarchical layout)
  algorithms/
    astar.py            A* with hazard-aware heuristic, evacuation mode
    csp.py              AC-3 + MRV/LCV backtracking CSP scheduler
    bayesian.py         Noisy-OR Bayesian network inference
  models/
    mine_graph.py       Graph data structures (nodes, edges, adjacency)
  api/
    routes.py           REST endpoints
    websocket.py        WebSocket state streaming

frontend/
  src/
    App.jsx             Main layout, game mode panel, blast toggle, WebSocket
    components/
      MineMap.jsx       SVG mine map: zoom/pan, agents, cost labels, effects
      ControlPanel.jsx  Parameter sliders
      HazardDashboard.jsx  Bayesian inference display + sensor telemetry
      ScheduleView.jsx  CSP Gantt chart
      EventLog.jsx      Live event feed
    utils/
      api.js            Axios API client
      websocket.js      WebSocket hook
```

## Running the Project

Requires Python 3.11+ and Node 18+.

```bash
chmod +x run.sh
./run.sh
```

This starts:
- Backend at `http://localhost:8000`
- Frontend at `http://localhost:5173`

## Controls

| Action | How |
|---|---|
| Generate mine | Click **GENERATE** |
| Start/pause simulation | Click **START / PAUSE** |
| Toggle blast operations | Click **💥 BLAST** in the HUD |
| Play game mode | Turn off blast, then click **🎮 GAME MODE** |
| Zoom map | Scroll wheel |
| Pan map | Click + drag |
| View CSP schedule | Click **SCHEDULE** |
