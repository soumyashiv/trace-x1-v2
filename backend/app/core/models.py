"""
Core dataclasses shared by every service in the pipeline.

These are deliberately framework-free (no Pydantic/SQLAlchemy) so the
analytics core can be unit-tested with nothing but the standard library
and can be reused unchanged by the FastAPI layer, a CLI, or a notebook.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Chain(str, Enum):
    ETH = "ETH"
    BTC = "BTC"
    TRON = "TRON"
    MOCK = "MOCK"


@dataclass(frozen=True)
class Transaction:
    """A single on-chain value transfer."""
    tx_hash: str
    chain: Chain
    from_address: str
    to_address: str
    value: float          # in native units (already decimal-adjusted)
    timestamp: datetime
    block_number: int
    fee: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tx_hash": self.tx_hash,
            "chain": self.chain.value,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "block_number": self.block_number,
            "fee": self.fee,
        }


@dataclass
class WalletLabel:
    """Ground-truth / heuristic metadata attached to an address by the
    label & cluster database. This is evidence, not a verdict."""
    address: str
    label: str                     # e.g. "known_exchange", "sanctioned", "mixer"
    entity_name: Optional[str] = None
    cluster_id: Optional[str] = None
    source: str = "internal_mock_db"
    confidence: float = 0.5
    last_verified: Optional[datetime] = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Case:
    case_id: str
    title: str
    investigator: str
    suspect_wallet: str
    chain: Chain
    created_at: datetime
    status: str = "open"
    notes: str = ""
