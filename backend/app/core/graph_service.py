"""
Builds a transaction graph from raw transfers and extracts the structural
signals the risk engine and VASP-attribution service need: hop distances,
fan-in/fan-out, intermediary candidates, and candidate suspicious paths
toward labelled (known exchange / mixer) nodes.

Pure NetworkX — no framework dependency, so it is directly unit-testable.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import networkx as nx

from app.core.models import Transaction


@dataclass
class WalletGraphStats:
    address: str
    in_degree: int = 0
    out_degree: int = 0
    fan_in: int = 0            # distinct senders
    fan_out: int = 0           # distinct receivers
    total_in_value: float = 0.0
    total_out_value: float = 0.0
    tx_count: int = 0
    hop_distance: int | None = None   # hops from the traced source wallet


def build_graph(transactions: list[Transaction]) -> nx.MultiDiGraph:
    """Build a directed multigraph: nodes = addresses, edges = transfers."""
    g = nx.MultiDiGraph()
    for tx in transactions:
        g.add_node(tx.from_address)
        g.add_node(tx.to_address)
        g.add_edge(
            tx.from_address,
            tx.to_address,
            tx_hash=tx.tx_hash,
            value=tx.value,
            timestamp=tx.timestamp,
            fee=tx.fee,
        )
    return g


def compute_hops(g: nx.MultiDiGraph, source: str) -> dict[str, int]:
    """BFS hop distance from `source`, following the direction money moves."""
    if source not in g:
        return {}
    lengths = nx.single_source_shortest_path_length(g, source)
    return dict(lengths)


def compute_wallet_stats(
    g: nx.MultiDiGraph, source: str
) -> dict[str, WalletGraphStats]:
    """Per-node structural stats used as risk-engine features."""
    hops = compute_hops(g, source)
    stats: dict[str, WalletGraphStats] = {}

    for node in g.nodes:
        senders = set()
        receivers = set()
        total_in = 0.0
        total_out = 0.0
        tx_count = 0

        for u, v, data in g.in_edges(node, data=True):
            senders.add(u)
            total_in += data.get("value", 0.0)
            tx_count += 1
        for u, v, data in g.out_edges(node, data=True):
            receivers.add(v)
            total_out += data.get("value", 0.0)
            tx_count += 1

        stats[node] = WalletGraphStats(
            address=node,
            in_degree=g.in_degree(node),
            out_degree=g.out_degree(node),
            fan_in=len(senders),
            fan_out=len(receivers),
            total_in_value=round(total_in, 8),
            total_out_value=round(total_out, 8),
            tx_count=tx_count,
            hop_distance=hops.get(node),
        )
    return stats


def detect_intermediaries(
    g: nx.MultiDiGraph, source: str, fan_out_threshold: int = 2
) -> list[str]:
    """
    A wallet is flagged as a candidate intermediary if it is reachable from
    the source, has both inbound and outbound activity (pass-through), and
    forwards funds onward within a short time window (checked by the risk
    engine's velocity feature — here we flag the structural shape only).
    """
    hops = compute_hops(g, source)
    candidates = []
    for node, hop in hops.items():
        if node == source or hop == 0:
            continue
        if g.in_degree(node) >= 1 and g.out_degree(node) >= 1:
            candidates.append(node)
    return candidates


def find_paths_to_labelled_nodes(
    g: nx.MultiDiGraph, source: str, labelled_addresses: set[str], max_paths: int = 5
) -> list[list[str]]:
    """All simple paths from `source` to any labelled (exchange/mixer) node,
    capped to keep this tractable on large graphs."""
    paths: list[list[str]] = []
    for target in labelled_addresses:
        if target not in g or source not in g:
            continue
        try:
            for path in nx.all_simple_paths(g, source, target, cutoff=6):
                paths.append(path)
                if len(paths) >= max_paths:
                    return paths
        except nx.NetworkXNoPath:
            continue
    return paths


def edge_timeline(g: nx.MultiDiGraph) -> list[dict]:
    """Flat, timestamp-sorted list of every edge, for the Timeline screen."""
    events = []
    for u, v, data in g.edges(data=True):
        events.append(
            {
                "tx_hash": data.get("tx_hash"),
                "from": u,
                "to": v,
                "value": data.get("value"),
                "timestamp": data.get("timestamp"),
            }
        )
    events.sort(key=lambda e: e["timestamp"])
    return events
