"""
Mine graph data structures.
Represents the mine as a weighted directed graph G(V, E).
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    JUNCTION = "junction"
    ORE_ZONE = "ore_zone"
    EXIT = "exit"


class MineNode(BaseModel):
    """A node in the mine graph."""
    id: str
    node_type: NodeType
    x: float  # 2D position for visualization + heuristic
    y: float
    hazard_probability: float = 0.0  # current P(hazard)
    label: str = ""
    is_blocked: bool = False

    def distance_to(self, other: "MineNode") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    class Config:
        use_enum_values = True


class MineEdge(BaseModel):
    """A directed edge in the mine graph."""
    source: str
    target: str
    distance: float
    gradient: float = 1.0       # multiplier: 1.0 = flat, >1 = uphill penalty
    condition_factor: float = 1.0  # multiplier: 1.0 = good, >1 = degraded

    @property
    def weight(self) -> float:
        """Composite edge weight: distance × gradient × condition."""
        return self.distance * self.gradient * self.condition_factor


class MineGraph(BaseModel):
    """
    Complete mine graph representation.
    Stores adjacency as dict[source_id → list[MineEdge]].
    """
    nodes: dict[str, MineNode] = Field(default_factory=dict)
    edges: dict[str, list[MineEdge]] = Field(default_factory=dict)

    # ── Node operations ──────────────────────────────────────────
    def add_node(self, node: MineNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self.edges:
            self.edges[node.id] = []

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        self.edges.pop(node_id, None)
        for src in list(self.edges.keys()):
            self.edges[src] = [e for e in self.edges[src] if e.target != node_id]

    def get_node(self, node_id: str) -> Optional[MineNode]:
        return self.nodes.get(node_id)

    # ── Edge operations ──────────────────────────────────────────
    def add_edge(self, edge: MineEdge) -> None:
        if edge.source not in self.edges:
            self.edges[edge.source] = []
        self.edges[edge.source].append(edge)

    def add_bidirectional_edge(self, source: str, target: str,
                                distance: float,
                                gradient: float = 1.0,
                                condition_factor: float = 1.0) -> None:
        self.add_edge(MineEdge(
            source=source, target=target,
            distance=distance, gradient=gradient,
            condition_factor=condition_factor,
        ))
        self.add_edge(MineEdge(
            source=target, target=source,
            distance=distance,
            gradient=max(0.5, 2.0 - gradient),  # inverse gradient for return
            condition_factor=condition_factor,
        ))

    def get_neighbors(self, node_id: str) -> list[tuple[str, MineEdge]]:
        """Return list of (neighbor_id, edge) pairs."""
        return [(e.target, e) for e in self.edges.get(node_id, [])]

    def get_adjacent_nodes(self, node_id: str) -> set[str]:
        """Get set of node IDs adjacent to given node (both directions)."""
        adjacent = set()
        for e in self.edges.get(node_id, []):
            adjacent.add(e.target)
        # Also check if any node has an edge TO this node
        for src, edge_list in self.edges.items():
            for e in edge_list:
                if e.target == node_id:
                    adjacent.add(src)
        return adjacent

    # ── Query helpers ────────────────────────────────────────────
    def get_nodes_by_type(self, node_type: NodeType) -> list[MineNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_exit_nodes(self) -> list[MineNode]:
        return self.get_nodes_by_type(NodeType.EXIT)

    def get_ore_zones(self) -> list[MineNode]:
        return self.get_nodes_by_type(NodeType.ORE_ZONE)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(el) for el in self.edges.values())

    def to_serializable(self) -> dict:
        """Convert to JSON-friendly dict for frontend."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "type": n.node_type,
                    "x": n.x,
                    "y": n.y,
                    "hazard_probability": n.hazard_probability,
                    "label": n.label,
                    "is_blocked": n.is_blocked,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "distance": round(e.distance, 1),
                    "gradient": round(e.gradient, 2),
                    "condition_factor": round(e.condition_factor, 2),
                    "weight": round(e.weight, 1),
                }
                for edge_list in self.edges.values()
                for e in edge_list
            ],
        }
