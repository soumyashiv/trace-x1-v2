"""
Orchestrates the end-to-end happy path required by the spec:

    case -> wallet -> transactions -> graph -> suspicious path -> risk
         -> VASP hypothesis -> report-ready case result

This module intentionally contains almost no logic of its own — it wires
together provider -> graph_service -> risk_service -> vasp_service so that
each stage stays independently testable, and the orchestration itself is
tested as an integration test (see tests/test_pipeline_happy_path.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.graph_service import (
    build_graph,
    compute_wallet_stats,
    detect_intermediaries,
    edge_timeline,
    find_paths_to_labelled_nodes,
)
from app.core.models import Transaction, WalletLabel
from app.core.provider import BlockchainProvider
from app.core.risk_service import RiskResult, score_wallet
from app.core.vasp_service import VaspAttribution, attribute_destination


@dataclass
class InvestigationResult:
    suspect_wallet: str
    transactions: list[Transaction]
    intermediaries: list[str]
    suspicious_paths: list[list[str]]
    wallet_risk: RiskResult
    intermediary_risks: list[RiskResult]
    vasp_attributions: list[VaspAttribution]
    timeline: list[dict]
    generated_at: datetime

    def top_finding_summary(self) -> str:
        best = self.vasp_attributions[0] if self.vasp_attributions else None
        if best and best.likely_entity:
            return (
                f"Suspect wallet {self.suspect_wallet} shows a "
                f"{self.wallet_risk.risk_level}-risk fund flow "
                f"({self.wallet_risk.risk_score:.1f}/100) with a "
                f"{best.confidence*100:.0f}% confidence hypothesis that funds "
                f"reached {best.likely_entity}."
            )
        return (
            f"Suspect wallet {self.suspect_wallet} shows a "
            f"{self.wallet_risk.risk_level}-risk fund flow "
            f"({self.wallet_risk.risk_score:.1f}/100); no known VASP match "
            "was found in this trace."
        )

    def to_dict(self) -> dict:
        return {
            "suspect_wallet": self.suspect_wallet,
            "transaction_count": len(self.transactions),
            "intermediaries": self.intermediaries,
            "suspicious_paths": self.suspicious_paths,
            "wallet_risk": self.wallet_risk.to_dict(),
            "intermediary_risks": [r.to_dict() for r in self.intermediary_risks],
            "vasp_attributions": [a.to_dict() for a in self.vasp_attributions],
            "timeline": [
                {**e, "timestamp": e["timestamp"].isoformat()} for e in self.timeline
            ],
            "generated_at": self.generated_at.isoformat(),
            "summary": self.top_finding_summary(),
        }


def run_investigation(
    suspect_wallet: str,
    provider: BlockchainProvider,
    tx_limit: int = 500,
) -> InvestigationResult:
    # Step 1: pull the raw transaction data through the provider abstraction.
    transactions = provider.get_transactions(suspect_wallet, limit=tx_limit)

    # Expand one hop further for every new address we discover, so the
    # graph isn't just a star centered on the suspect wallet. Two rounds
    # is enough for the MVP's synthetic/demo depth; see roadmap for a
    # proper bounded BFS crawl with budget controls for production data.
    seen_addresses = {suspect_wallet}
    frontier = {tx.to_address for tx in transactions} | {tx.from_address for tx in transactions}
    for _ in range(2):
        new_frontier = set()
        for addr in frontier - seen_addresses:
            seen_addresses.add(addr)
            more = provider.get_transactions(addr, limit=tx_limit)
            transactions.extend(more)
            new_frontier |= {t.to_address for t in more} | {t.from_address for t in more}
        frontier = new_frontier

    # de-duplicate by tx_hash (multiple expansion rounds can re-fetch edges)
    unique: dict[str, Transaction] = {tx.tx_hash: tx for tx in transactions}
    transactions = list(unique.values())

    # Step 2: build the transaction graph.
    graph = build_graph(transactions)

    # Step 3: label lookup for every node we've seen (evidence-backed DB).
    label_lookup: dict[str, WalletLabel] = {}
    for addr in graph.nodes:
        label = provider.get_wallet_label(addr)
        if label:
            label_lookup[addr] = label

    # Step 4: identify intermediaries and candidate suspicious paths.
    intermediaries = detect_intermediaries(graph, suspect_wallet)
    suspicious_paths = find_paths_to_labelled_nodes(
        graph, suspect_wallet, set(label_lookup.keys())
    )

    # Step 5: explainable risk score for the suspect wallet itself...
    wallet_risk = score_wallet(
        suspect_wallet, transactions, graph, suspect_wallet, label_lookup
    )
    # ...and for every flagged intermediary, so the UI can render risk per node.
    intermediary_risks = [
        score_wallet(addr, transactions, graph, suspect_wallet, label_lookup)
        for addr in intermediaries
    ]

    # Step 6: evidence-backed VASP/entity attribution hypotheses.
    vasp_attributions = attribute_destination(graph, suspect_wallet, label_lookup)

    # Step 7: timeline for the Timeline screen.
    timeline = edge_timeline(graph)

    return InvestigationResult(
        suspect_wallet=suspect_wallet,
        transactions=transactions,
        intermediaries=intermediaries,
        suspicious_paths=suspicious_paths,
        wallet_risk=wallet_risk,
        intermediary_risks=intermediary_risks,
        vasp_attributions=vasp_attributions,
        timeline=timeline,
        generated_at=datetime.now(timezone.utc),
    )
