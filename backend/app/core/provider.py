"""
Blockchain data-access layer.

TRACE-X never talks to a chain directly from business logic. Every service
depends on the `BlockchainProvider` interface, so an outage or missing API
key for a real provider degrades gracefully instead of crashing the app.

Implementations:
- MockBlockchainProvider: deterministic synthetic data generator. Same
  wallet address -> same graph, every time, on every machine, with no
  network access. This is what powers the offline demo.
- EVMBlockchainProvider: talks to a real EVM-compatible chain via web3.py
  / an Etherscan-style REST API. Requires credentials. If they are not
  configured, it raises `ProviderUnavailableError` rather than silently
  returning empty/fake data, so the caller can fall back explicitly.
"""
from __future__ import annotations

import hashlib
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from app.core.models import Chain, Transaction, WalletLabel


class ProviderUnavailableError(RuntimeError):
    """Raised when a real provider cannot serve a request (no credentials,
    network failure, rate limit, upstream outage). Callers should catch
    this and fail *loudly and explicitly* to the investigator UI rather
    than pretending the trace is complete."""


class BlockchainProvider(ABC):
    """Abstraction every graph/risk/attribution service depends on."""

    name: str = "abstract"

    @abstractmethod
    def get_transactions(
        self, address: str, limit: int = 500
    ) -> list[Transaction]:
        """Return known transactions touching `address` (in or out)."""

    @abstractmethod
    def get_wallet_label(self, address: str) -> Optional[WalletLabel]:
        """Return known label/cluster evidence for `address`, or None."""

    @abstractmethod
    def is_healthy(self) -> bool:
        """Cheap liveness check used by the /system/health screen."""


# --------------------------------------------------------------------------- #
# Mock provider — deterministic, offline, used for the demo dataset and tests
# --------------------------------------------------------------------------- #

# A small mock "label & cluster" database. In production this would be an
# evidence-backed table populated from sanctions lists, exchange disclosures,
# clustering heuristics (common-input-ownership, change detection, etc.),
# and analyst annotations — never asserted as ground truth on its own.
_MOCK_LABEL_DB: dict[str, WalletLabel] = {
    "0xEXCHANGE_KRAKENISH_HOT1": WalletLabel(
        address="0xEXCHANGE_KRAKENISH_HOT1",
        label="known_exchange",
        entity_name="Krakenish Exchange (mock)",
        cluster_id="cluster-exch-01",
        source="mock_vasp_registry_v1",
        confidence=0.9,
        last_verified=datetime(2026, 8, 1),
        evidence=[
            "Address tagged by mock_vasp_registry_v1 as a Krakenish hot wallet",
            "Receives from >500 distinct counterparties (deposit-hub pattern)",
        ],
    ),
    "0xMIXER_TORNADO_LIKE": WalletLabel(
        address="0xMIXER_TORNADO_LIKE",
        label="mixer",
        entity_name="Unidentified mixing service (mock)",
        cluster_id="cluster-mixer-01",
        source="mock_vasp_registry_v1",
        confidence=0.7,
        last_verified=datetime(2026, 7, 15),
        evidence=["Fixed-denomination deposits, delayed matched withdrawals"],
    ),
}


class MockBlockchainProvider(BlockchainProvider):
    """
    Deterministic synthetic provider.

    Given the SAME seed address, this always regenerates the SAME wallet
    graph: victim wallet -> burner -> 2-3 intermediary hops -> known
    exchange cluster, plus some innocuous noise edges. This determinism is
    what lets the offline demo and the unit tests be reproducible.
    """

    name = "mock"

    def __init__(self, seed_prefix: str = "trace-x-demo"):
        self._seed_prefix = seed_prefix

    def is_healthy(self) -> bool:
        return True

    def get_wallet_label(self, address: str) -> Optional[WalletLabel]:
        return _MOCK_LABEL_DB.get(address)

    def _rng_for(self, address: str) -> random.Random:
        digest = hashlib.sha256(f"{self._seed_prefix}:{address}".encode()).hexdigest()
        return random.Random(int(digest[:16], 16))

    def get_transactions(self, address: str, limit: int = 500) -> list[Transaction]:
        """
        Deterministically synthesize a laundering-style fund-flow rooted at
        `address`:

            victim_wallet --(burst)--> burner
            burner --(split, fast)--> intermediary_1, intermediary_2
            intermediary_1 --(hop)--> intermediary_3
            intermediary_2, intermediary_3 --(converge)--> known exchange
            + a handful of unrelated noise edges for realism
        """
        rng = self._rng_for(address)
        base_time = datetime(2026, 6, 1, 8, 0, 0)

        burner = f"0xBURNER_{address[-6:]}"
        inter1 = f"0xINTER1_{address[-6:]}"
        inter2 = f"0xINTER2_{address[-6:]}"
        inter3 = f"0xINTER3_{address[-6:]}"
        exchange = "0xEXCHANGE_KRAKENISH_HOT1"
        noise_peer = f"0xPEER_{address[-6:]}"

        initial_value = round(rng.uniform(8_000, 20_000), 2)

        txs: list[Transaction] = []

        def add(frm, to, value, minutes_offset, block, fee=0.0):
            txs.append(
                Transaction(
                    tx_hash=hashlib.sha1(
                        f"{frm}{to}{value}{minutes_offset}".encode()
                    ).hexdigest()[:16],
                    chain=Chain.MOCK,
                    from_address=frm,
                    to_address=to,
                    value=value,
                    timestamp=base_time + timedelta(minutes=minutes_offset),
                    block_number=block,
                    fee=fee,
                )
            )

        # Stage 0: victim -> burner (a fast, out-of-character burst)
        add(address, burner, initial_value, 0, 1000001)
        add(address, burner, round(initial_value * 0.15, 2), 4, 1000002)

        # Stage 1: burner splits funds fast across two intermediaries (fan-out)
        split1 = round(initial_value * 0.55, 2)
        split2 = round(initial_value * 0.45, 2)
        add(burner, inter1, split1, 9, 1000003)
        add(burner, inter2, split2, 11, 1000004)

        # Stage 2: inter1 hops once more before converging (extra hop = evasion)
        add(inter1, inter3, round(split1 * 0.97, 2), 25, 1000009)

        # Stage 3: convergence onto a known exchange deposit hub (fan-in)
        add(inter3, exchange, round(split1 * 0.95, 2), 40, 1000015)
        add(inter2, exchange, round(split2 * 0.96, 2), 42, 1000016)

        # Noise: an unrelated, slow, low-value transfer — should NOT be
        # flagged as part of the suspicious path.
        add(address, noise_peer, round(rng.uniform(5, 50), 2), 60 * 24 * 3, 1002000)

        return txs[:limit]


# --------------------------------------------------------------------------- #
# Real EVM provider — requires credentials, fails loudly if unavailable
# --------------------------------------------------------------------------- #


class EVMBlockchainProvider(BlockchainProvider):
    """
    Real provider for EVM-compatible chains (Ethereum, Polygon, BSC, ...).

    Uses web3.py against an RPC endpoint plus an Etherscan-style explorer
    API for historical transfer indexing (raw JSON-RPC does not give you an
    efficient "all transactions for an address" query). Both are read from
    environment variables and NEVER hardcoded.

    IMPORTANT (honesty requirement): this class does not fabricate data.
    If `TRACEX_EVM_RPC_URL` / `TRACEX_EXPLORER_API_KEY` are not configured,
    or the upstream call fails, it raises `ProviderUnavailableError`. The
    caller (see `app.core.pipeline`) is responsible for surfacing that to
    the investigator instead of silently substituting mock data.
    """

    name = "evm"

    def __init__(self):
        self._rpc_url = os.environ.get("TRACEX_EVM_RPC_URL")
        self._explorer_api_key = os.environ.get("TRACEX_EXPLORER_API_KEY")
        self._explorer_base_url = os.environ.get(
            "TRACEX_EXPLORER_BASE_URL", "https://api.etherscan.io/api"
        )
        self._web3 = None
        if self._rpc_url:
            try:
                from web3 import Web3  # imported lazily: optional dependency

                self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
            except ImportError:
                # web3.py not installed in this environment — provider is
                # configured but unusable; treat as unavailable, not fatal.
                self._web3 = None

    def is_healthy(self) -> bool:
        if not self._rpc_url or not self._explorer_api_key:
            return False
        if self._web3 is None:
            return False
        try:
            return bool(self._web3.is_connected())
        except Exception:
            return False

    def _require_configured(self):
        if not self._rpc_url or not self._explorer_api_key:
            raise ProviderUnavailableError(
                "EVMBlockchainProvider is not configured: set "
                "TRACEX_EVM_RPC_URL and TRACEX_EXPLORER_API_KEY. "
                "Falling back to the mock provider is the caller's decision, "
                "not this class's."
            )

    def get_transactions(self, address: str, limit: int = 500) -> list[Transaction]:
        self._require_configured()
        try:
            import requests

            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99_999_999,
                "sort": "asc",
                "apikey": self._explorer_api_key,
            }
            resp = requests.get(self._explorer_base_url, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("status") != "1":
                raise ProviderUnavailableError(
                    f"Explorer API returned no data / error: {payload.get('message')}"
                )
            out: list[Transaction] = []
            for row in payload.get("result", [])[:limit]:
                out.append(
                    Transaction(
                        tx_hash=row["hash"],
                        chain=Chain.ETH,
                        from_address=row["from"],
                        to_address=row["to"],
                        value=float(row["value"]) / 1e18,
                        timestamp=datetime.utcfromtimestamp(int(row["timeStamp"])),
                        block_number=int(row["blockNumber"]),
                        fee=float(row.get("gasUsed", 0)) * float(row.get("gasPrice", 0)) / 1e18,
                    )
                )
            return out
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # network error, malformed response, etc.
            raise ProviderUnavailableError(str(exc)) from exc

    def get_wallet_label(self, address: str) -> Optional[WalletLabel]:
        # Real deployments would hit an internal evidence-backed label
        # service here (see docs/limitations.md). Not implemented for the
        # prototype — returning None is honest; inventing a label is not.
        self._require_configured()
        return None
