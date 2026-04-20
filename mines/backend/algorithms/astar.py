"""
A* Search Module — Routing Engine

Implements A* pathfinding with three modes:
  1. Normal:     Standard A* with composite edge weights
  2. Hazard:     Hazard-aware with λ-weighted hazard penalties
  3. Evacuation: Hazard-aware, preferring exit nodes

Cost function:
  g(n) = Σ(distance × gradient × condition) along path
  + λ × P(hazard) for hazard/evacuation modes

Heuristic:
  Normal:     h(n) = euclidean(n, goal)
  Hazard:     h(n) = euclidean(n, goal) + λ × P(hazard at n)
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Optional

from models.mine_graph import MineGraph, MineNode, NodeType


@dataclass(order=True)
class _AStarNode:
    """Internal priority queue entry."""
    f_cost: float
    g_cost: float = field(compare=False)
    node_id: str = field(compare=False)
    parent: Optional[str] = field(default=None, compare=False)


@dataclass
class AStarResult:
    """Result of an A* search."""
    path: list[str]  # ordered node IDs from start to goal
    total_cost: float
    nodes_explored: int
    success: bool
    mode: str
    fallback_node: Optional[str] = None  # if path blocked, nearest safe node


def astar_search(
    graph: MineGraph,
    start: str,
    goal: str,
    mode: str = "normal",
    hazard_lambda: float = 2.0,
    hazard_threshold: float = 0.6,
    blocked_threshold: float = 0.9,
) -> AStarResult:
    """
    Run A* search on the mine graph.

    Args:
        graph: The mine graph
        start: Start node ID
        goal: Goal node ID
        mode: 'normal', 'hazard', or 'evacuation'
        hazard_lambda: Weight for hazard cost in hazard/evacuation modes
        hazard_threshold: Hazard probability above which cost is penalized
        blocked_threshold: Hazard probability above which node is impassable

    Returns:
        AStarResult with path, cost, and metadata
    """
    start_node = graph.get_node(start)
    goal_node = graph.get_node(goal)

    if not start_node or not goal_node:
        return AStarResult(
            path=[], total_cost=float("inf"),
            nodes_explored=0, success=False, mode=mode,
        )

    open_set: list[_AStarNode] = []
    g_costs: dict[str, float] = {start: 0.0}
    came_from: dict[str, Optional[str]] = {start: None}
    closed_set: set[str] = set()
    nodes_explored = 0

    h_start = _heuristic(start_node, goal_node, graph, mode, hazard_lambda)
    heapq.heappush(open_set, _AStarNode(
        f_cost=h_start, g_cost=0.0, node_id=start,
    ))

    while open_set:
        current = heapq.heappop(open_set)
        current_id = current.node_id
        nodes_explored += 1

        if current_id in closed_set:
            continue
        closed_set.add(current_id)

        # Goal reached
        if current_id == goal:
            path = _reconstruct_path(came_from, goal)
            return AStarResult(
                path=path,
                total_cost=round(current.g_cost, 4),
                nodes_explored=nodes_explored,
                success=True,
                mode=mode,
            )

        # Expand neighbors
        for neighbor_id, edge in graph.get_neighbors(current_id):
            if neighbor_id in closed_set:
                continue

            neighbor_node = graph.get_node(neighbor_id)
            if not neighbor_node:
                continue

            # Check if node is blocked (hazard too high)
            if mode in ("hazard", "evacuation"):
                if neighbor_node.hazard_probability >= blocked_threshold:
                    if neighbor_node.node_type != NodeType.EXIT:
                        continue  # skip blocked nodes (exits always accessible)

            # Compute g cost
            edge_cost = edge.weight
            if mode in ("hazard", "evacuation"):
                hp = neighbor_node.hazard_probability
                if hp > hazard_threshold:
                    edge_cost += hazard_lambda * hp * 100.0  # heavy penalty
                else:
                    edge_cost += hazard_lambda * hp

            tentative_g = g_costs[current_id] + edge_cost

            if tentative_g < g_costs.get(neighbor_id, float("inf")):
                g_costs[neighbor_id] = tentative_g
                came_from[neighbor_id] = current_id
                h = _heuristic(neighbor_node, goal_node, graph, mode, hazard_lambda)
                f = tentative_g + h
                heapq.heappush(open_set, _AStarNode(
                    f_cost=f, g_cost=tentative_g, node_id=neighbor_id,
                ))

    # Path not found — find nearest safe node (fallback)
    fallback = _find_nearest_safe_node(graph, start, closed_set)
    return AStarResult(
        path=[], total_cost=float("inf"),
        nodes_explored=nodes_explored, success=False,
        mode=mode, fallback_node=fallback,
    )


def find_evacuation_path(
    graph: MineGraph,
    start: str,
    hazard_lambda: float = 3.0,
    hazard_threshold: float = 0.5,
    blocked_threshold: float = 0.85,
) -> AStarResult:
    """
    Find the best evacuation path from start to the nearest exit.
    Tries all exits and returns the path with lowest cost.
    """
    exits = graph.get_exit_nodes()
    if not exits:
        return AStarResult(
            path=[], total_cost=float("inf"),
            nodes_explored=0, success=False, mode="evacuation",
        )

    best_result = AStarResult(
        path=[], total_cost=float("inf"),
        nodes_explored=0, success=False, mode="evacuation",
    )

    total_explored = 0
    for exit_node in exits:
        result = astar_search(
            graph, start, exit_node.id,
            mode="evacuation",
            hazard_lambda=hazard_lambda,
            hazard_threshold=hazard_threshold,
            blocked_threshold=blocked_threshold,
        )
        total_explored += result.nodes_explored
        if result.success and result.total_cost < best_result.total_cost:
            best_result = result

    best_result.nodes_explored = total_explored
    if not best_result.success:
        # All exits blocked — find nearest safe node
        best_result.fallback_node = _find_nearest_safe_node(
            graph, start, set(),
        )
    return best_result


def _heuristic(
    node: MineNode,
    goal: MineNode,
    graph: MineGraph,
    mode: str,
    hazard_lambda: float,
) -> float:
    """Compute heuristic h(n)."""
    dist = node.distance_to(goal)
    if mode == "normal":
        return dist
    # Hazard-aware heuristic
    return dist + hazard_lambda * node.hazard_probability


def _reconstruct_path(came_from: dict[str, Optional[str]], goal: str) -> list[str]:
    """Reconstruct path from came_from map."""
    path = []
    current: Optional[str] = goal
    while current is not None:
        path.append(current)
        current = came_from.get(current)
    path.reverse()
    return path


def _find_nearest_safe_node(
    graph: MineGraph,
    start: str,
    explored: set[str],
) -> Optional[str]:
    """
    Find the nearest reachable node with low hazard.
    Used as fallback when no path to goal exists.
    """
    # BFS from start to find closest safe node
    visited: set[str] = set()
    queue: list[tuple[str, float]] = [(start, 0.0)]
    best_node: Optional[str] = None
    best_score = float("inf")

    while queue:
        current_id, dist = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        node = graph.get_node(current_id)
        if not node:
            continue

        # Score: lower hazard + closer = better
        score = dist + node.hazard_probability * 100.0
        if score < best_score and node.hazard_probability < 0.5:
            best_score = score
            best_node = current_id

        for neighbor_id, edge in graph.get_neighbors(current_id):
            if neighbor_id not in visited:
                queue.append((neighbor_id, dist + edge.distance))

    return best_node
