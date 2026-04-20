"""
CSP Solver Module — Scheduler

Solves the constraint satisfaction problem of scheduling mine operations.

Variables : (zone_id, time_slot)
Domains   : ["blast", "drill", "load", "idle"] per variable
             (reduced to ["halted"] when hazard probability exceeds threshold)

Constraints:
  1. Adjacency    — Adjacent zones cannot both blast in the same time slot.
  2. Capacity     — At most N non-idle zones may be active in any one slot.
  3. Cooldown     — A zone cannot blast in two consecutive slots.
  4. Hazard       — If hazard > threshold the domain collapses to ["halted"].
  5. Sequence     — Preferred order per zone: blast → drill → load (soft).

Algorithms used:
  • AC-3   — Forward arc-consistency propagation before backtracking.
  • MRV    — Minimum Remaining Values variable ordering heuristic.
  • LCV    — Least Constraining Value domain ordering (simplified).
  • Backtracking with forward-checking.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from models.mine_graph import MineGraph
from config import config

Activity = str
Variable = Tuple[str, int]          # (zone_id, time_slot)
Domain   = List[Activity]
Assignment = Dict[Variable, Activity]


# ── AC-3 ──────────────────────────────────────────────────────────────────────

def ac3(
    domains: Dict[Variable, Domain],
    adjacencies: Dict[str, Set[str]],
    _variables: List[Variable],
    num_slots: int,
) -> bool:
    """
    Run AC-3 arc-consistency algorithm.

    Enforces binary blast-adjacency constraints and blast-cooldown constraints.
    Modifies *domains* in-place.

    Returns False if any domain becomes empty (problem unsolvable without
    relaxation); True otherwise.
    """
    # Build arc queue: arcs (Xi, Xj) where a binary constraint exists.
    queue: deque[Tuple[Variable, Variable]] = deque()

    # Adjacency arcs (same time slot, adjacent zones)
    zone_list = list(adjacencies.keys())
    for t in range(num_slots):
        for zi in zone_list:
            for zj in adjacencies[zi]:
                if (zi, t) in domains and (zj, t) in domains:
                    queue.append(((zi, t), (zj, t)))

    # Cooldown arcs (same zone, consecutive slots)
    for zi in zone_list:
        for t in range(num_slots - 1):
            if (zi, t) in domains and (zi, t + 1) in domains:
                queue.append(((zi, t), (zi, t + 1)))
                queue.append(((zi, t + 1), (zi, t)))

    while queue:
        xi, xj = queue.popleft()
        if _revise(domains, xi, xj, adjacencies):
            if not domains[xi]:
                return False  # domain wiped out → inconsistent
            # Re-add arcs (xk, xi) for all xk ≠ xj that share a constraint with xi
            zi, ti = xi
            zj, tj = xj
            # Adjacency arcs for xi
            if ti == tj:  # same-slot adjacency case
                for zk in adjacencies.get(zi, set()):
                    xk = (zk, ti)
                    if xk != xj and xk in domains:
                        queue.append((xk, xi))
            # Cooldown arcs for xi
            for dt in (-1, +1):
                xk = (zi, ti + dt)
                if xk != xj and xk in domains:
                    queue.append((xk, xi))

    return True


def _revise(
    domains: Dict[Variable, Domain],
    xi: Variable,
    xj: Variable,
    adjacencies: Dict[str, Set[str]],
) -> bool:
    """
    Remove values from domains[xi] that have no support in domains[xj].
    Returns True if the domain of xi was changed.
    """
    zi, ti = xi
    zj, tj = xj
    revised = False
    to_remove: List[Activity] = []

    for vi in domains[xi]:
        # Check whether there exists at least one vj in domains[xj]
        # consistent with (xi=vi, xj=vj).
        has_support = False
        for vj in domains[xj]:
            if _binary_consistent(zi, ti, vi, zj, tj, vj, adjacencies):
                has_support = True
                break
        if not has_support:
            to_remove.append(vi)
            revised = True

    for v in to_remove:
        domains[xi].remove(v)

    return revised


def _binary_consistent(
    zi: str, ti: int, vi: Activity,
    zj: str, tj: int, vj: Activity,
    adjacencies: Dict[str, Set[str]],
) -> bool:
    """
    Check whether the pair (zi@ti=vi, zj@tj=vj) satisfies all binary
    constraints that apply between these two variables.
    """
    # Both values are always consistent if one is "halted" or "idle"
    if vi in ("halted", "idle") or vj in ("halted", "idle"):
        return True

    # Blast-adjacency constraint: same time slot, adjacent zones
    if ti == tj and zi != zj:
        if vi == "blast" and vj == "blast" and zj in adjacencies.get(zi, set()):
            return False

    # Cooldown constraint: same zone, consecutive slots
    if zi == zj and abs(ti - tj) == 1:
        if vi == "blast" and vj == "blast":
            return False

    return True


# ── CSP Solver ────────────────────────────────────────────────────────────────

class CSPSolver:
    def __init__(
        self,
        graph: MineGraph,
        zones: List[str],
        num_slots: int,
        hazard_state: Dict[str, float],
        hazard_threshold: float = config.hazard.hazard_threshold,
        capacity: int = config.schedule.processing_capacity,
        blast_enabled: bool = True,
    ):
        self.graph = graph
        self.zones = zones
        self.num_slots = num_slots
        self.hazard_state = hazard_state
        self.hazard_threshold = hazard_threshold
        self.capacity = capacity
        self.blast_enabled = blast_enabled

        self.variables: List[Variable] = [
            (z, t) for z in zones for t in range(num_slots)
        ]
        # Precompute per-zone adjacencies (only zones in scope, not all graph nodes)
        self.adjacencies: Dict[str, Set[str]] = {
            z: self.graph.get_adjacent_nodes(z) & set(zones)
            for z in zones
        }
        self.domains: Dict[Variable, Domain] = self._initialize_domains()

    # ── Domain initialisation ──────────────────────────────────────────────

    def _initialize_domains(self) -> Dict[Variable, Domain]:
        domains: Dict[Variable, Domain] = {}
        for var in self.variables:
            zone_id, _ = var
            if self.hazard_state.get(zone_id, 0.0) >= self.hazard_threshold:
                domains[var] = ["halted"]
            elif self.blast_enabled:
                domains[var] = ["blast", "drill", "load", "idle"]
            else:
                domains[var] = ["drill", "load", "idle"]
        return domains

    # ── Public entry point ─────────────────────────────────────────────────

    def solve(self) -> Optional[Assignment]:
        """
        Run AC-3 preprocessing then backtracking search.
        Returns a complete assignment or None if unsatisfiable.
        """
        # Deep-copy domains so AC-3 modifications are on a working copy
        working_domains = {var: list(d) for var, d in self.domains.items()}

        consistent = ac3(working_domains, self.adjacencies, self.variables, self.num_slots)
        if not consistent:
            # AC-3 detected an empty domain → fall back immediately
            return None

        return self._backtrack({}, working_domains)

    # ── Backtracking ───────────────────────────────────────────────────────

    def _backtrack(
        self,
        assignment: Assignment,
        domains: Dict[Variable, Domain],
    ) -> Optional[Assignment]:

        if len(assignment) == len(self.variables):
            return assignment

        var = self._select_unassigned(assignment, domains)
        if var is None:
            return None

        for value in self._order_domain_values(var, assignment, domains):
            if self._is_consistent(var, value, assignment):
                assignment[var] = value

                # Forward checking: prune affected variables
                pruned = self._forward_check(var, value, assignment, domains)

                if all(len(domains[v]) > 0 for v in self.variables if v not in assignment):
                    result = self._backtrack(assignment, domains)
                    if result is not None:
                        return result

                # Undo forward checking pruning
                del assignment[var]
                self._restore_pruned(pruned, domains)

        return None

    # ── MRV variable ordering ──────────────────────────────────────────────

    def _select_unassigned(
        self,
        assignment: Assignment,
        domains: Dict[Variable, Domain],
    ) -> Optional[Variable]:
        unassigned = [v for v in self.variables if v not in assignment]
        if not unassigned:
            return None
        # MRV: smallest remaining domain
        return min(unassigned, key=lambda v: len(domains[v]))

    # ── LCV domain ordering ────────────────────────────────────────────────

    def _order_domain_values(
        self,
        var: Variable,
        _assignment: Assignment,
        domains: Dict[Variable, Domain],
    ) -> List[Activity]:
        """Prefer values that constrain neighbours least (simplified LCV)."""
        preferred = ["blast", "drill", "load", "idle", "halted"]
        domain = domains[var]
        return sorted(
            domain,
            key=lambda a: preferred.index(a) if a in preferred else 99,
        )

    # ── Consistency check ──────────────────────────────────────────────────

    def _is_consistent(
        self,
        var: Variable,
        value: Activity,
        assignment: Assignment,
    ) -> bool:
        zone_id, time_slot = var

        if value in ("halted", "idle"):
            return True

        if value == "blast":
            # No adjacent blast in the same slot
            for adj_zone in self.adjacencies[zone_id]:
                if assignment.get((adj_zone, time_slot)) == "blast":
                    return False
            # No blast in the previous slot (cooldown)
            if time_slot > 0:
                if assignment.get((zone_id, time_slot - 1)) == "blast":
                    return False
            # No blast in the next slot (cooldown, if already assigned)
            if assignment.get((zone_id, time_slot + 1)) == "blast":
                return False

        # Capacity: max N non-idle zones per slot
        active = sum(
            1 for (z, t), v in assignment.items()
            if t == time_slot and v not in ("idle", "halted")
        )
        if active + 1 > self.capacity:
            return False

        return True

    # ── Forward checking ───────────────────────────────────────────────────

    def _forward_check(
        self,
        var: Variable,
        value: Activity,
        assignment: Assignment,
        domains: Dict[Variable, Domain],
    ) -> Dict[Variable, List[Activity]]:
        """
        Prune values from unassigned neighbours that are now inconsistent.
        Returns a dict of {variable: pruned_values} for backtracking undo.
        """
        pruned: Dict[Variable, List[Activity]] = {}
        zone_id, time_slot = var

        if value == "blast":
            # Remove "blast" from adjacent zones in the same slot
            for adj_zone in self.adjacencies[zone_id]:
                nb = (adj_zone, time_slot)
                if nb not in assignment and nb in domains:
                    if "blast" in domains[nb]:
                        pruned.setdefault(nb, []).append("blast")
                        domains[nb].remove("blast")

            # Remove "blast" from consecutive slots of the same zone
            for dt in (-1, +1):
                nb = (zone_id, time_slot + dt)
                if nb not in assignment and nb in domains:
                    if "blast" in domains[nb]:
                        pruned.setdefault(nb, []).append("blast")
                        domains[nb].remove("blast")

        return pruned

    def _restore_pruned(
        self,
        pruned: Dict[Variable, List[Activity]],
        domains: Dict[Variable, Domain],
    ) -> None:
        for var, values in pruned.items():
            domains[var].extend(values)


# ── Public helper ─────────────────────────────────────────────────────────────

def compute_schedule(
    graph: MineGraph,
    zones: List[str],
    num_slots: int,
    hazard_state: Dict[str, float],
    blast_enabled: bool = True,
) -> List[dict]:
    """
    Run the CSP solver and return a flat list of schedule entries.
    Falls back to a safe idle/halted schedule if unsatisfiable.
    """
    solver = CSPSolver(graph, zones, num_slots, hazard_state, blast_enabled=blast_enabled)
    assignment = solver.solve()

    if assignment is None:
        # Partial fallback: everything idle or halted
        assignment = {}
        for var in solver.variables:
            z, _ = var
            assignment[var] = (
                "halted"
                if hazard_state.get(z, 0.0) >= solver.hazard_threshold
                else "idle"
            )

    result = [
        {
            "zone_id": zone_id,
            "time_slot": time_slot,
            "activity": activity,
            "equipment_id": None,
        }
        for (zone_id, time_slot), activity in assignment.items()
    ]
    result.sort(key=lambda x: (x["zone_id"], x["time_slot"]))
    return result
