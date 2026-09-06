"""
VASP / entity attribution.

Produces a *hypothesis*, never a verdict. Per the problem statement's
critical requirement, this module must not represent an attribution as
guaranteed truth — every result carries supporting evidence,
contradicting evidence (if any), a confidence figure, and provenance
(source + last_verified date) so an investigator can judge it themselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import networkx as nx

from app.core.models import WalletLabel


@dataclass
class VaspAttribution:
    target_address: str
    likely_entity: str | None
    confidence: float
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    last_verified: str | None
    source: str | None

    def to_dict(self) -> dict:
        return {
            "target_address": self.target_address,
            "likely_entity": self.likely_entity,
            "confidence": round(self.confidence, 2),
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "last_verified": self.last_verified,
            "source": self.source,
            "disclaimer": (
                "This is an evidence-based hypothesis, not a confirmed "
                "identification. Confidence decays with hop distance and "
                "with any funds routed through unresolved mixers/bridges."
            ),
        }


def attribute_destination(
    graph: nx.MultiDiGraph,
    source_address: str,
    label_lookup: dict[str, WalletLabel],
) -> list[VaspAttribution]:
    """
    For every labelled node reachable from `source_address`, build an
    attribution hypothesis. Confidence decays with hop distance and is
    reduced further if the path crosses a wallet labelled as a mixer
    (since provenance is genuinely weaker after a mixing hop).
    """
    results: list[VaspAttribution] = []
    if source_address not in graph:
        return results

    for addr, label in label_lookup.items():
        if addr not in graph or label.label not in ("known_exchange",):
            continue
        try:
            path = nx.shortest_path(graph, source_address, addr)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

        hop_count = len(path) - 1
        crosses_mixer = any(
            label_lookup.get(n) and label_lookup[n].label == "mixer" for n in path
        )

        base_confidence = label.confidence
        decay = max(0.0, 1.0 - 0.12 * hop_count)
        confidence = base_confidence * decay
        contradicting: list[str] = []
        if crosses_mixer:
            confidence *= 0.5
            contradicting.append(
                "Path crosses a wallet labelled as a mixing service; "
                "true final destination cannot be fully confirmed past that point"
            )

        supporting = [
            f"Direct on-chain path found: {' -> '.join(path)} ({hop_count} hop(s))",
            *label.evidence,
            f"Entity label confidence from {label.source}: {label.confidence:.2f}",
        ]

        results.append(
            VaspAttribution(
                target_address=addr,
                likely_entity=label.entity_name,
                confidence=max(0.05, min(0.99, confidence)),
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
                last_verified=label.last_verified.isoformat() if label.last_verified else None,
                source=label.source,
            )
        )

    if not results:
        results.append(
            VaspAttribution(
                target_address=source_address,
                likely_entity=None,
                confidence=0.0,
                supporting_evidence=[],
                contradicting_evidence=[
                    "No path to any address in the known VASP/cluster "
                    "database was found within the traced graph. This does "
                    "NOT mean the funds are untraceable — only that this "
                    "trace, with this data source, found no match."
                ],
                last_verified=None,
                source=None,
            )
        )

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
