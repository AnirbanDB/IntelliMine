"""
Mine Graph Engine — Procedural generation of mine tunnel networks.

Generates a realistic weighted directed graph representing an underground mine
with junctions, ore zones, and exit points.

Layout strategy: layered hierarchical placement to minimise edge crossings.
  Layer 0 (y≈60):  EXIT nodes
  Layer 1 (y≈180): top junction row
  Layer 2 (y≈300): middle junction row
  Layer 3 (y≈420): bottom junction row / entry to ore zones
  Layer 4 (y≈540): ORE_ZONE nodes
Edges are only drawn between adjacent layers (N → N+1) plus a small fraction
of same-layer "horizontal tunnel" shortcuts between close neighbours.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Optional

from models.mine_graph import MineGraph, MineNode, MineEdge, NodeType
from config import config

# ── Canvas / layer constants ──────────────────────────────────────────────────
_CANVAS_W = 900.0
_CANVAS_H = 620.0
_LAYER_Y   = [60.0, 180.0, 300.0, 420.0, 540.0]   # y centre for each layer
_MIN_HGAP  = 110.0   # minimum horizontal gap between nodes in same layer
_JITTER    = 20.0    # ±px random jitter applied after placement
_MAX_DEGREE = 4      # cap on edges per node (shortcuts only; layer edges ignore)


def generate_mine(
    num_junctions: Optional[int] = None,
    num_ore_zones: Optional[int] = None,
    num_exits: Optional[int] = None,
    width: float = 800.0,
    height: float = 600.0,
    connectivity: Optional[float] = None,
    seed: Optional[int] = None,
) -> MineGraph:
    """
    Procedurally generate a mine graph.

    The mine is laid out in a 2D space with:
    - Exit nodes at the top (surface)
    - Ore zones deeper (lower y values / mapped to bottom)
    - Junctions connecting everything

    Args:
        num_junctions: Number of junction nodes
        num_ore_zones: Number of ore zone nodes
        num_exits: Number of exit/surface nodes
        width: Canvas width for node placement (kept for API compatibility)
        height: Canvas height for node placement (kept for API compatibility)
        connectivity: Probability of connecting nearby nodes (scales shortcuts)
        seed: Random seed for reproducibility
    """
    cfg = config.mine
    num_junctions = num_junctions or cfg.num_junctions
    num_ore_zones = num_ore_zones or cfg.num_ore_zones
    num_exits     = num_exits     or cfg.num_exits
    connectivity  = connectivity  or cfg.connectivity

    if seed is not None:
        random.seed(seed)

    graph = MineGraph()

    # ── Distribute junctions across three middle layers ─────────────────────
    # Layer 1, 2, 3 each get roughly equal shares; round-robin remainder.
    j_per_layer = [num_junctions // 3] * 3
    for k in range(num_junctions % 3):
        j_per_layer[k] += 1

    # ── Build layer lists of MineNode ────────────────────────────────────────
    layers: list[list[MineNode]] = [[] for _ in range(5)]

    # Layer 0 — exits
    for i in range(num_exits):
        node = MineNode(
            id=f"exit_{i}",
            node_type=NodeType.EXIT,
            x=0.0,   # placed properly below
            y=0.0,
            label=f"Exit {i + 1}",
            hazard_probability=0.0,
        )
        layers[0].append(node)

    # Layers 1-3 — junctions
    for layer_idx, count in enumerate(j_per_layer, start=1):
        for i in range(count):
            global_i = sum(j_per_layer[:layer_idx - 1]) + i
            node = MineNode(
                id=f"junc_{global_i}",
                node_type=NodeType.JUNCTION,
                x=0.0,
                y=0.0,
                label=f"Junction {global_i + 1}",
                hazard_probability=random.uniform(0.0, 0.15),
            )
            layers[layer_idx].append(node)

    # Layer 4 — ore zones
    for i in range(num_ore_zones):
        node = MineNode(
            id=f"ore_{i}",
            node_type=NodeType.ORE_ZONE,
            x=0.0,
            y=0.0,
            label=f"Ore Zone {i + 1}",
            hazard_probability=random.uniform(0.05, 0.25),
        )
        layers[4].append(node)

    # ── Assign (x, y) positions using evenly spaced + jitter ────────────────
    # Derive per-call layer Y positions scaled to the requested canvas height.
    layer_ys = _compute_layer_ys(height)
    for layer_idx, layer_nodes in enumerate(layers):
        _place_layer(layer_nodes, layer_idx, width, layer_ys)
        for node in layer_nodes:
            graph.add_node(node)

    # ── Connect adjacent layers (N → N+1) ────────────────────────────────────
    _connect_adjacent_layers(graph, layers)

    # ── Same-layer shortcut edges (horizontal tunnels) ───────────────────────
    shortcut_prob = 0.30 * (connectivity / 0.35)   # scale with connectivity
    _add_shortcut_edges(graph, layers, shortcut_prob)

    # ── Ensure full connectivity ──────────────────────────────────────────────
    all_nodes: list[MineNode] = [n for layer in layers for n in layer]
    _ensure_connectivity(graph, all_nodes)

    # ── Ensure every exit can reach every ore zone ───────────────────────────
    _ensure_exit_ore_paths(graph, all_nodes)

    return graph


# ── Layout helpers ────────────────────────────────────────────────────────────

def _compute_layer_ys(height: float) -> list[float]:
    """Return the 5 layer Y centres scaled to the given canvas height."""
    # Reference positions are defined for _CANVAS_H; scale proportionally.
    return [round(y * height / _CANVAS_H, 1) for y in _LAYER_Y]


def _place_layer(
    nodes: list[MineNode],
    layer_idx: int,
    canvas_w: float,
    layer_ys: list[float],
) -> None:
    """Evenly space nodes in a layer with small random jitter."""
    n = len(nodes)
    if n == 0:
        return

    y_centre = layer_ys[layer_idx]
    margin = 60.0

    if n == 1:
        positions = [canvas_w / 2.0]
    else:
        step = max(_MIN_HGAP, (canvas_w - 2 * margin) / (n - 1))
        # Centre the spread on the canvas
        total_span = step * (n - 1)
        x_start = (canvas_w - total_span) / 2.0
        positions = [x_start + i * step for i in range(n)]

    for node, x in zip(nodes, positions):
        jx = random.uniform(-_JITTER, _JITTER)
        jy = random.uniform(-_JITTER, _JITTER)
        node.x = round(max(margin, min(canvas_w - margin, x + jx)), 1)
        node.y = round(y_centre + jy, 1)


# ── Edge-building helpers ─────────────────────────────────────────────────────

def _connect_adjacent_layers(
    graph: MineGraph,
    layers: list[list[MineNode]],
) -> None:
    """
    Connect every node in layer N to at least 2 nodes in layer N+1
    (and every node in layer N+1 to at least 2 nodes in layer N).
    Uses nearest-neighbour matching to minimise crossing.
    """
    for layer_idx in range(len(layers) - 1):
        upper = layers[layer_idx]      # layer N
        lower = layers[layer_idx + 1]  # layer N+1

        if not upper or not lower:
            continue

        # Sort both layers by x so nearest-neighbour wiring is naturally ordered
        upper_sorted = sorted(upper, key=lambda n: n.x)
        lower_sorted = sorted(lower, key=lambda n: n.x)

        # Track how many connections each node already has in this cross-layer
        upper_conn: dict[str, int] = {n.id: 0 for n in upper_sorted}
        lower_conn: dict[str, int] = {n.id: 0 for n in lower_sorted}
        connected_pairs: set[tuple[str, str]] = set()

        def _add_pair(u: MineNode, lo: MineNode) -> None:
            key = (u.id, lo.id)
            if key in connected_pairs:
                return
            connected_pairs.add(key)
            upper_conn[u.id] += 1
            lower_conn[lo.id] += 1
            dist = u.distance_to(lo)
            grad = _compute_gradient(u, lo)
            cond = round(random.uniform(0.8, 1.3), 2)
            graph.add_bidirectional_edge(
                source=u.id, target=lo.id,
                distance=round(dist, 1),
                gradient=round(grad, 2),
                condition_factor=cond,
            )

        # Primary wiring: each upper node connects to its 2 nearest lower nodes
        for u in upper_sorted:
            nearest = sorted(lower_sorted, key=lambda lo: abs(lo.x - u.x))
            for lo in nearest[:2]:
                _add_pair(u, lo)

        # Guarantee: each lower node has at least 2 upper connections
        for lo in lower_sorted:
            if lower_conn[lo.id] >= 2:
                continue
            needed = 2 - lower_conn[lo.id]
            candidates = sorted(
                upper_sorted,
                key=lambda u: abs(u.x - lo.x),
            )
            for u in candidates:
                if needed <= 0:
                    break
                _add_pair(u, lo)
                needed -= 1


def _add_shortcut_edges(
    graph: MineGraph,
    layers: list[list[MineNode]],
    shortcut_prob: float,
) -> None:
    """
    Add horizontal tunnel edges between close neighbours in the same layer.
    Only added when both endpoints have fewer than _MAX_DEGREE cross-edges
    and the nodes are within 1.5 × _MIN_HGAP of each other.
    """
    max_shortcut_dist = _MIN_HGAP * 1.5

    def _degree(node_id: str) -> int:
        return len(graph.edges.get(node_id, []))

    for layer_nodes in layers:
        sorted_nodes = sorted(layer_nodes, key=lambda n: n.x)
        for i in range(len(sorted_nodes) - 1):
            a = sorted_nodes[i]
            b = sorted_nodes[i + 1]   # immediate neighbour only
            dist = a.distance_to(b)
            if dist > max_shortcut_dist:
                continue
            if _degree(a.id) >= _MAX_DEGREE or _degree(b.id) >= _MAX_DEGREE:
                continue
            if random.random() > shortcut_prob:
                continue
            # Check pair not already connected
            existing = {e.target for e in graph.edges.get(a.id, [])}
            if b.id in existing:
                continue
            grad = _compute_gradient(a, b)
            cond = round(random.uniform(0.9, 1.1), 2)
            graph.add_bidirectional_edge(
                source=a.id, target=b.id,
                distance=round(dist, 1),
                gradient=round(grad, 2),
                condition_factor=cond,
            )


def _compute_gradient(a: MineNode, b: MineNode) -> float:
    """
    Compute gradient multiplier based on vertical difference.
    Going down (higher y) is easier, going up is harder.
    """
    dy   = b.y - a.y   # positive = going deeper
    dist = a.distance_to(b)
    if dist < 1:
        return 1.0
    slope = dy / dist
    # flat=1.0, uphill>1.0, downhill<1.0
    return max(0.6, 1.0 - slope * 0.5)


# ── Connectivity guarantees ───────────────────────────────────────────────────

def _ensure_connectivity(graph: MineGraph, nodes: list[MineNode]) -> None:
    """Ensure the graph is fully connected using BFS + bridge edges."""
    if not nodes:
        return

    visited: set[str] = set()
    components: list[list[str]] = []

    for node in nodes:
        if node.id in visited:
            continue
        component: list[str] = []
        queue: deque[str] = deque([node.id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            for neighbor_id, _ in graph.get_neighbors(current):
                if neighbor_id not in visited:
                    queue.append(neighbor_id)
        components.append(component)

    # Connect components by adding edges between closest nodes
    while len(components) > 1:
        comp_a = components[0]
        best_dist = float("inf")
        best_pair = (comp_a[0], components[1][0])
        best_comp_idx = 1

        for ci in range(1, len(components)):
            comp_b = components[ci]
            for a_id in comp_a:
                node_a = graph.get_node(a_id)
                if not node_a:
                    continue
                for b_id in comp_b:
                    node_b = graph.get_node(b_id)
                    if not node_b:
                        continue
                    d = node_a.distance_to(node_b)
                    if d < best_dist:
                        best_dist = d
                        best_pair = (a_id, b_id)
                        best_comp_idx = ci

        node_a = graph.get_node(best_pair[0])
        node_b = graph.get_node(best_pair[1])
        if node_a and node_b:
            gradient = _compute_gradient(node_a, node_b)
            graph.add_bidirectional_edge(
                source=best_pair[0],
                target=best_pair[1],
                distance=round(best_dist, 1),
                gradient=round(gradient, 2),
                condition_factor=round(random.uniform(0.9, 1.2), 2),
            )

        components[0] = comp_a + components[best_comp_idx]
        components.pop(best_comp_idx)


def _ensure_exit_ore_paths(graph: MineGraph, nodes: list[MineNode]) -> None:
    """Ensure at least one exit can reach each ore zone."""
    exits = [n for n in nodes if n.node_type == NodeType.EXIT]
    ores  = [n for n in nodes if n.node_type == NodeType.ORE_ZONE]

    if not exits or not ores:
        return

    for ore in ores:
        visited: set[str] = set()
        queue: deque[str] = deque([ore.id])
        found_exit = False
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            node = graph.get_node(current)
            if node and node.node_type == NodeType.EXIT:
                found_exit = True
                break
            for neighbor_id, _ in graph.get_neighbors(current):
                if neighbor_id not in visited:
                    queue.append(neighbor_id)

        if not found_exit:
            nearest_exit = min(exits, key=lambda e: e.distance_to(ore))
            dist = nearest_exit.distance_to(ore)
            gradient = _compute_gradient(nearest_exit, ore)
            graph.add_bidirectional_edge(
                source=nearest_exit.id,
                target=ore.id,
                distance=round(dist, 1),
                gradient=round(gradient, 2),
                condition_factor=1.0,
            )
