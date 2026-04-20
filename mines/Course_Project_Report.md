# Course Project Report

## Title of the Project
**IntelliMine: AI-Driven Mine Operations Simulator using A* Search, CSP Scheduling, and Bayesian Hazard Inference**

## Sl. No. Name of Student Roll Number Department
| Sl. No. | Name of Student | Roll Number | Department |
|---|---|---|---|
| 1 | Student Name 1 | Roll No. 1 | Department 1 |
| 2 | Student Name 2 | Roll No. 2 | Department 2 |
| 3 | Student Name 3 | Roll No. 3 | Department 3 |
| 4 | Student Name 4 | Roll No. 4 | Department 4 |

---

## 1 Problem Formulation

- **Real-world problem (formal):**
  - Underground mine operations require simultaneous decisions for routing, safety monitoring, and activity scheduling.
  - Let $G=(V,E)$ be the mine graph where nodes are junctions/ore zones/exits and edges are tunnels with weighted traversal cost.
  - At each simulation tick $t$, the system must:
    1. estimate risk $P(\text{hazard}\mid\text{sensor evidence})$ for each node,
    2. compute safe/efficient agent routes,
    3. compute conflict-free operation schedules under constraints.

- **Why this is important and interesting:**
  - Mining is safety-critical and cost-sensitive.
  - Wrong routing or scheduling can cause evacuation delays, productivity loss, and increased hazard exposure.
  - The project demonstrates how AI methods can jointly optimize **safety + efficiency** in a dynamic environment.

- **Interdisciplinary significance:**
  - Combines graph search (AI planning), probabilistic reasoning (uncertainty modeling), and combinatorial optimization (constraint solving).
  - Blends software engineering, operations research, and safety engineering.

- **Inputs, outputs, and decision process:**
  - **Inputs:** mine topology, sensor readings (gas, vibration, moisture, blast activity), simulation parameters, agent states.
  - **Outputs:** hazard probabilities, truck/worker paths, slot-wise zone activities, live event stream, full simulation state.
  - **Decision process:** Bayesian update → CSP scheduling → A* route planning → agent movement update.

- **Problem characterization:**
  - **Stochastic:** yes (sensor drift, random hazard emergence, randomized generation).
  - **Dynamic:** yes (state evolves every tick).
  - **Discrete:** mostly discrete decision variables (nodes, slots, activities).
  - **Constrained:** yes (adjacency blast rule, cooldown, capacity, hazard threshold).
  - **Partially deterministic:** path planning over a fixed graph is deterministic for fixed costs; costs change with hazard state.

---

## 2 Method and Justification

### Why This Method is Appropriate

- **A* Search** matches shortest/safest path planning on weighted graphs.
  - Strength: optimality under admissible conditions and practical efficiency.
  - In this project, cost reflects physical tunnel effort and hazard penalty.

- **CSP with AC-3 + Backtracking (MRV/LCV)** matches slot-assignment with hard logical constraints.
  - Strength: explicit feasibility guarantees and interpretable constraints.
  - AC-3 reduces search space before backtracking.

- **Bayesian-style probabilistic hazard model** matches uncertain sensor-driven risk.
  - Strength: interpretable probability outputs and smooth integration into planning/scheduling.

- **Feasibility and interpretability:**
  - All three methods are computationally manageable for real-time simulation scales.
  - Outputs are human-readable (path, risk probability, schedule table), suitable for dashboards.

### Algorithm Design and Methodology

**Pipeline:**
1. Generate/reset mine graph and spawn agents.
2. Initialize sensor readings.
3. Infer node-wise hazard probabilities from sensor evidence.
4. Build CSP schedule for ore zones over time slots.
5. Plan truck paths (and evacuation paths when needed).
6. Advance simulation one tick at a time and stream state to clients via WebSocket.

### Algorithm 1 Integrated Mine Decision Pipeline

**Require:** Mine config, simulation config, hazard config, schedule config, sensor evidence, current state

**Ensure:** Updated safe paths, feasible schedule, hazard-aware state evolution

1: Initialize graph, agents, sensor map, and state variables  
2: Construct initial hazard probabilities from current evidence  
3: while simulation status is RUNNING do  
4: Evolve sensor readings and detect spikes  
5: Recompute Bayesian hazard probabilities  
6: Compute CSP schedule with hazard constraints  
7: Plan/repair A* routes for trucks and evacuation paths for workers  
8: Advance agent positions and operational states  
9: if severe hazard condition is satisfied then  
10: Trigger evacuation logic and log critical event  
11: end if  
12: Broadcast full serializable state via WebSocket  
13: end while  
14: Return stopped/paused state snapshot

---

## 3 Implementation Details

### System Design

- **Backend framework:** FastAPI + Pydantic models.
- **Real-time streaming:** WebSocket broadcaster sends full state continuously.
- **Core engine:** Tick-based simulation orchestrator.

### Major modules/functions

- **Application entry:** [backend/main.py](backend/main.py)
  - Creates app, CORS middleware, includes REST and WebSocket routes.
  - Initializes global `SimulationEngine` in lifespan hook.

- **REST API:** [backend/api/routes.py](backend/api/routes.py)
  - `/generate-mine`, `/run-simulation`, `/update-parameters`, `/simulation-state`, `/compute-path`, `/compute-schedule`, `/compute-hazard`, `/mine-graph`, `/solve-path`.

- **Streaming API:** [backend/api/websocket.py](backend/api/websocket.py)
  - `/ws/live-state` for continuous live updates.

- **Simulation orchestrator:** [backend/engine/simulation.py](backend/engine/simulation.py)
  - `initialize()`, `start()`, `pause()`, `stop()`, `tick()`, hazard/schedule/path update internals.

- **Graph generation:** [backend/engine/graph_engine.py](backend/engine/graph_engine.py)
  - Layered procedural mine creation and connectivity guarantees.

- **Algorithms:**
  - A*: [backend/algorithms/astar.py](backend/algorithms/astar.py)
  - CSP: [backend/algorithms/csp.py](backend/algorithms/csp.py)
  - Bayesian hazard: [backend/algorithms/bayesian.py](backend/algorithms/bayesian.py)

- **Data models:**
  - Graph, nodes, edges: [backend/models/mine_graph.py](backend/models/mine_graph.py)
  - Agents: [backend/models/agents.py](backend/models/agents.py)
  - Hazards/sensors: [backend/models/hazards.py](backend/models/hazards.py)
  - Full state snapshot: [backend/models/simulation_state.py](backend/models/simulation_state.py)

### Key data structures

- `MineGraph`: adjacency map `edges: dict[source -> list[MineEdge]]`.
- `SimulationState`: single source of truth for tick, graph, agents, hazards, schedule, paths, logs, parameters.
- `hazard_probabilities: dict[node_id -> float]` used by both A* and CSP.
- CSP variables: `(zone_id, time_slot)` with activity domains.

### GitHub Repository

- Provide the repository link.
- Repository includes code, documentation, and README.

Repository Link: https://github.com/your-repository-link

---

## 4 Results and Performance Analysis

### Experimental Setup

- **Scenarios:** random mine topologies with configurable junctions/ore zones/exits.
- **Execution model:** tick-driven backend loop with WebSocket streaming.
- **Typical software stack:** Python 3.11+, FastAPI, React + Vite frontend.
- **Evaluation metrics:**
  - Path cost and nodes explored (A*),
  - Feasible assignment rate (CSP),
  - Hazard probability trends,
  - Evacuation success, event frequency, UI responsiveness.

### Quantitative Results

Use the following tables/plots for your final submission run:

1. **A* routing metrics table**
   - Columns: scenario, mode (`normal`/`hazard`/`evacuation`), path length, total cost, nodes explored, runtime.

2. **CSP scheduling quality table**
   - Columns: scenario, slots, zones, constraints violated (expected 0), active utilization, halted-zone count.

3. **Hazard inference trend plot**
   - Per-node $P(\text{OverallHazard})$ vs tick.

4. **Safety outcome table**
   - Columns: scenario, hazards triggered, evacuations triggered, successful evacuations, trapped agents.

5. **System responsiveness**
   - API response times and WebSocket update interval consistency.

---

## API Usage Guide (after starting the app)

Backend base URL: `http://localhost:8000/api`  
Swagger UI: `http://localhost:8000/docs`

### Typical order

1. **Generate mine**
   - `POST /generate-mine`
   - Body (optional):
     ```json
     { "seed": 42 }
     ```
   - You can also send `{}`.

2. **Start simulation**
   - `POST /run-simulation`
   - Body:
     ```json
     { "action": "start" }
     ```

3. **Pause / Stop**
   - Pause:
     ```json
     { "action": "pause" }
     ```
   - Stop:
     ```json
     { "action": "stop" }
     ```

4. **Get full state snapshot**
   - `GET /simulation-state`

5. **Update parameters dynamically**
   - `POST /update-parameters`
   - Example:
     ```json
     {
       "params": {
         "simulation": { "num_trucks": 5, "tick_rate_ms": 250 },
         "hazard": { "hazard_threshold": 0.65 },
         "schedule": { "blast_enabled": true }
       }
     }
     ```

6. **Run algorithms directly**
   - A*: `POST /compute-path`
   - CSP: `POST /compute-schedule`
   - Hazard inference: `POST /compute-hazard`

7. **Real-time stream**
   - WebSocket: `ws://localhost:8000/ws/live-state`

### Fix applied for `/api/run-simulation` 400 issue

- The endpoint now accepts empty body/default action and action aliases.
- Supported values now include:
  - `start`, `pause`, `stop`
  - aliases: `resume`, `run`, `play` (mapped to `start`)
- If you send `{}`, it defaults to `start`.

---

## Notes for submission

- Replace student details and repository link before final submission.
- Add your own measured result tables and graphs from actual runs.
