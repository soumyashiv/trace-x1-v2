"""
Deterministic synthetic demo cases. Everything here works fully offline —
no network calls — via MockBlockchainProvider.
"""
from __future__ import annotations

from datetime import datetime

from app.core.models import Case, Chain

DEMO_WALLETS = {
    "case-demo-001": "0xVICTIM0000000000000000000000000000A1",
    "case-demo-002": "0xVICTIM0000000000000000000000000000B2",
}


def build_demo_case(case_id: str = "case-demo-001") -> Case:
    wallet = DEMO_WALLETS.get(case_id, DEMO_WALLETS["case-demo-001"])
    return Case(
        case_id=case_id,
        title="Reported crypto investment scam",
        investigator="demo.investigator",
        suspect_wallet=wallet,
        chain=Chain.MOCK,
        created_at=datetime(2026, 8, 20, 10, 0, 0),
        status="open",
        notes="Victim reported wallet after a fake trading-platform scam.",
    )
