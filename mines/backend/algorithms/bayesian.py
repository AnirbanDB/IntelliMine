"""
Bayesian Network Module — Hazard Reasoning

Computes the probability of a hazard event given sensor evidence.
Network structure:
GasLevel ──┐
           ├──► ToxicHazard
BlastActivity┘        │
                      ├──► OverallHazard
Vibration ──┐         │
            ├──► CollapseRisk ──┘
Moisture ───┘
"""

from typing import Dict

class Node:
    def __init__(self, name: str):
        self.name = name

# Simplified inference engine for this specific topology
# We avoid heavy external libs and implement exact inference natively.

def compute_hazard_probabilities(evidence: Dict[str, float]) -> Dict[str, float]:
    """
    Given evidence (sensor readings), compute posterior probabilities
    for intermediate risks and the final OverallHazard.

    Inputs (evidence dict):
      - gas_level: [0, 1]
      - blast_activity: [0, 1]
      - vibration: [0, 1]
      - moisture: [0, 1]

    Outputs (dict):
      - ToxicHazard: P
      - CollapseRisk: P
      - OverallHazard: P
    """
    g = evidence.get("gas_level", 0.0)
    b = evidence.get("blast_activity", 0.0)
    v = evidence.get("vibration", 0.0)
    m = evidence.get("moisture", 0.0)

    # ToxicHazard CPT approximation
    # P(ToxicHazard | GasLevel, BlastActivity)
    # Gas alone is bad. Blast activity (dust/fumes) exacerbates it.
    p_toxic = min(1.0, g * 0.7 + b * 0.3 + (g * b) * 0.5)

    # CollapseRisk CPT approximation
    # P(CollapseRisk | Vibration, Moisture)
    # Moisture weakens rock, vibration triggers it. Highly synergistic.
    p_collapse = min(1.0, v * 0.6 + m * 0.2 + (v * m) * 0.8)

    # OverallHazard
    # P(OverallHazard | ToxicHazard, CollapseRisk)
    # If either is high, overall hazard is high (noisy-OR pattern).
    # P(A or B) = P(A) + P(B) - P(A and B)
    p_overall = p_toxic + p_collapse - (p_toxic * p_collapse)

    return {
        "ToxicHazard": p_toxic,
        "CollapseRisk": p_collapse,
        "OverallHazard": p_overall
    }

def update_mine_hazard_states(graph_nodes: list, sensor_readings: Dict[str, dict]) -> Dict[str, float]:
    """
    Update hazard probability for all nodes given current sensor readings.
    Returns map of node_id -> OverallHazard probability.
    """
    hazard_probs = {}
    for node in graph_nodes:
        # Default evidence if no sensor reading exists
        evidence = sensor_readings.get(node.id, {
            "gas_level": 0.1,
            "blast_activity": 0.0,
            "vibration": 0.0,
            "moisture": 0.1
        })
        
        evidence_data = evidence
        if hasattr(evidence, "to_evidence_dict"):
            evidence_data = evidence.to_evidence_dict()
            
        probs = compute_hazard_probabilities(evidence_data)
        hazard_probs[node.id] = probs["OverallHazard"]
        
    return hazard_probs
