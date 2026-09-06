"""
Explainable, feature-based wallet risk scoring.

Design constraint from the problem statement: "Never return an unexplained
risk score." Every score this module produces is accompanied by a per-
feature contribution breakdown, the evidence that drove it, and a
confidence figure that reflects how much data was actually available.

This is deliberately a transparent weighted-feature model rather than an
opaque classifier. A gradient-boosted model (XGBoost/LightGBM) can be
trained later on labelled historical cases and plugged in behind the same
`score_wallet()` interface — see docs/roadmap.md — but it would need a
SHAP-style explanation layer to satisfy the same "never unexplained"
requirement, so it is out of scope for the MVP happy path.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime

import networkx as nx

from app.core.graph_service import WalletGraphStats, compute_hops
from app.core.models import Transaction, WalletLabel

# Feature weights. Kept as named constants (not magic numbers) so the
# Risk Analysis screen can render "why" in the same language as the code.
WEIGHTS = {
    "burstiness": 0.15,
    "hop_evasion": 0.12,
    "fan_out": 0.13,
    "fan_in": 0.08,
    "velocity": 0.15,
    "value_concentration": 0.10,
    "counterparty_diversity": 0.07,
    "known_risk_label": 0.25,
    "cluster_proximity": 0.10,
    "routing_irregularity": 0.10,
}
# Note: weights are allowed to sum to > 1.0; the raw weighted sum is
# clipped to [0, 100] after scaling. This keeps a single very strong
# signal (e.g. a direct hop to a sanctioned address) able to dominate,
# which matches investigator intuition better than forcing a convex
# combination.


@dataclass
class RiskResult:
    address: str
    risk_score: float                 # 0-100
    risk_level: str                   # low / medium / high / critical
    feature_contributions: dict[str, float]
    raw_features: dict[str, float]
    evidence: list[str]
    confidence: float                 # 0-1, reflects data completeness

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "feature_contributions": {
                k: round(v, 2) for k, v in self.feature_contributions.items()
            },
            "raw_features": {k: round(v, 4) for k, v in self.raw_features.items()},
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
        }


def _risk_level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _burstiness(timestamps: list[datetime]) -> float:
    """0-1: how tightly clustered in time transactions are. High burstiness
    (many transfers in a short window) is a classic layering signal."""
    if len(timestamps) < 2:
        return 0.0
    ordered = sorted(timestamps)
    deltas = [
        (b - a).total_seconds() for a, b in zip(ordered, ordered[1:])
    ]
    mean_delta = statistics.mean(deltas) if deltas else 0.0
    if mean_delta <= 0:
        return 1.0
    # Short mean inter-arrival time -> higher burstiness. 10 minutes (600s)
    # is treated as the "very bursty" reference point.
    return max(0.0, min(1.0, 600.0 / (mean_delta + 1e-6)))


def score_wallet(
    address: str,
    transactions: list[Transaction],
    graph: nx.MultiDiGraph,
    source_address: str,
    label_lookup: dict[str, WalletLabel],
) -> RiskResult:
    """
    Compute an explainable risk score for `address` within the context of
    the traced graph rooted at `source_address`.
    """
    evidence: list[str] = []
    raw: dict[str, float] = {}

    related = [
        tx
        for tx in transactions
        if tx.from_address == address or tx.to_address == address
    ]
    timestamps = [tx.timestamp for tx in related]

    # --- structural features from the graph ---
    fan_in = graph.in_degree(address) if address in graph else 0
    fan_out = graph.out_degree(address) if address in graph else 0
    hops = compute_hops(graph, source_address)
    hop_distance = hops.get(address)

    raw["burstiness"] = _burstiness(timestamps)
    raw["fan_out"] = min(1.0, fan_out / 5.0)
    raw["fan_in"] = min(1.0, fan_in / 5.0)
    raw["counterparty_diversity"] = min(
        1.0, len({t.from_address for t in related} | {t.to_address for t in related}) / 6.0
    )

    # hop_evasion: more hops from the reported victim wallet = more layering
    if hop_distance is None:
        raw["hop_evasion"] = 0.0
    else:
        raw["hop_evasion"] = min(1.0, hop_distance / 4.0)
        if hop_distance >= 2:
            evidence.append(
                f"{address} is {hop_distance} hops from the reported suspect wallet"
            )

    # velocity: value moved out relative to time since first inbound funds
    inbound = sorted([t for t in related if t.to_address == address], key=lambda t: t.timestamp)
    outbound = sorted([t for t in related if t.from_address == address], key=lambda t: t.timestamp)
    if inbound and outbound:
        first_in = inbound[0].timestamp
        first_out = outbound[0].timestamp
        delay_minutes = max((first_out - first_in).total_seconds() / 60.0, 0.01)
        raw["velocity"] = max(0.0, min(1.0, 30.0 / delay_minutes))
        if delay_minutes <= 15:
            evidence.append(
                f"Funds forwarded within {delay_minutes:.1f} minutes of receipt "
                "(pass-through / layering pattern)"
            )
    else:
        raw["velocity"] = 0.0

    # value_concentration: share of outbound value sent to the single
    # largest counterparty (a proxy for deliberate consolidation)
    if outbound:
        by_dest: dict[str, float] = {}
        for t in outbound:
            by_dest[t.to_address] = by_dest.get(t.to_address, 0.0) + t.value
        total_out = sum(by_dest.values()) or 1.0
        raw["value_concentration"] = max(by_dest.values()) / total_out
    else:
        raw["value_concentration"] = 0.0

    # known_risk_label: direct hit against the evidence-backed label DB
    label = label_lookup.get(address)
    if label:
        raw["known_risk_label"] = label.confidence
        evidence.append(
            f"Address labelled '{label.label}'"
            + (f" ({label.entity_name})" if label.entity_name else "")
            + f" by {label.source}, confidence {label.confidence:.2f}"
        )
        evidence.extend(label.evidence)
    else:
        raw["known_risk_label"] = 0.0

    # cluster_proximity: distance-decayed proximity to ANY labelled node
    labelled_nodes = [a for a in label_lookup if a in graph]
    if labelled_nodes:
        best = None
        for ln in labelled_nodes:
            if ln == address:
                continue
            try:
                d = nx.shortest_path_length(graph, address, ln)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            if best is None or d < best:
                best = d
        if best is not None:
            raw["cluster_proximity"] = max(0.0, 1.0 - (best / 4.0))
            if 0 < best <= 2:
                evidence.append(
                    f"{address} is {best} hop(s) from a labelled entity in the graph"
                )
        else:
            raw["cluster_proximity"] = 0.0
    else:
        raw["cluster_proximity"] = 0.0

    # routing_irregularity: pass-through node with near-equal in/out value
    # (classic layering wallet: money arrives and leaves almost intact)
    total_in_val = sum(t.value for t in inbound)
    total_out_val = sum(t.value for t in outbound)
    if total_in_val > 0 and total_out_val > 0:
        ratio = min(total_in_val, total_out_val) / max(total_in_val, total_out_val)
        raw["routing_irregularity"] = ratio if ratio > 0.85 else ratio * 0.3
        if ratio > 0.85:
            evidence.append(
                f"Near pass-through wallet: {total_in_val:.2f} in vs "
                f"{total_out_val:.2f} out ({ratio*100:.1f}% retained/forwarded)"
            )
    else:
        raw["routing_irregularity"] = 0.0

    # --- combine ---
    contributions = {k: raw.get(k, 0.0) * w * 100 for k, w in WEIGHTS.items()}
    score = sum(contributions.values())
    score = max(0.0, min(100.0, score))

    # confidence reflects how much real evidence we had to work with
    data_points = len(related) + (1 if label else 0)
    confidence = max(0.2, min(0.98, data_points / 10.0))

    if not evidence:
        evidence.append(
            "No strong individual signal fired; score reflects a weighted "
            "combination of weak structural indicators only."
        )

    return RiskResult(
        address=address,
        risk_score=score,
        risk_level=_risk_level(score),
        feature_contributions=contributions,
        raw_features=raw,
        evidence=evidence,
        confidence=confidence,
    )
