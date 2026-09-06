"""
Integration adapters for external investigative systems: NCRP (National
Cybercrime Reporting Portal) and SAHYOG.

HONESTY NOTE: TRACE-X does not have credentialed access to real NCRP or
SAHYOG APIs. These are MOCK connectors that implement the interface a real
integration would need, so the rest of the app (case intake, evidence
export) can be wired against a stable contract now and switched to a real
backend later without touching calling code. Do not deploy these to
production and do not present their output as live government data.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NcrpComplaintRef:
    complaint_id: str
    filed_at: datetime
    victim_reported_wallet: str
    status: str
    source: str = "mock_ncrp_connector"


class NcrpConnector(ABC):
    """Interface a real NCRP integration would implement: pulling a
    victim's complaint record (with consent/authorization) to pre-fill a
    TRACE-X case, and pushing case updates back."""

    @abstractmethod
    def fetch_complaint(self, complaint_id: str) -> NcrpComplaintRef | None: ...

    @abstractmethod
    def push_case_update(self, complaint_id: str, status: str, note: str) -> bool: ...


class MockNcrpConnector(NcrpConnector):
    def fetch_complaint(self, complaint_id: str) -> NcrpComplaintRef | None:
        # Deterministic mock lookup — no network call, no real complaint data.
        if not complaint_id.startswith("NCRP-"):
            return None
        return NcrpComplaintRef(
            complaint_id=complaint_id,
            filed_at=datetime(2026, 8, 15, 9, 30),
            victim_reported_wallet="0xVICTIM0000000000000000000000000000A1",
            status="under_review",
        )

    def push_case_update(self, complaint_id: str, status: str, note: str) -> bool:
        # In the mock connector this is a no-op that always "succeeds" so the
        # UI flow can be demonstrated end to end. Real integration requires
        # NCRP API credentials and an approved data-sharing agreement.
        return True


@dataclass
class SahyogAlert:
    alert_id: str
    entity_hint: str
    severity: str
    issued_at: datetime
    source: str = "mock_sahyog_connector"


class SahyogConnector(ABC):
    """Interface for pulling inter-agency SAHYOG coordination alerts
    relevant to a traced entity (e.g. an exchange already under multi-state
    investigation)."""

    @abstractmethod
    def lookup_entity_alerts(self, entity_name: str) -> list[SahyogAlert]: ...


class MockSahyogConnector(SahyogConnector):
    _MOCK_ALERTS = {
        "Krakenish Exchange (mock)": [
            SahyogAlert(
                alert_id="SAHYOG-MOCK-001",
                entity_hint="Krakenish Exchange (mock)",
                severity="medium",
                issued_at=datetime(2026, 7, 20),
            )
        ]
    }

    def lookup_entity_alerts(self, entity_name: str) -> list[SahyogAlert]:
        return self._MOCK_ALERTS.get(entity_name, [])
