from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_role
from app.api.cache import cached_json
from app.api.schemas import InvestigationRunRequest
from app.core.pipeline import run_investigation
from app.core.provider import MockBlockchainProvider, ProviderUnavailableError
from app.db.models import CaseRecord, InvestigationRun
from app.db.session import get_db

router = APIRouter(prefix="/cases/{case_id}/investigation", tags=["investigation"])

# Provider selection is intentionally centralized here. Swapping the mock
# provider for EVMBlockchainProvider (or a router that tries real first and
# falls back to mock with a visible warning) is a one-line change.
_provider = MockBlockchainProvider()


def _get_case_or_404(case_id: str, db: Session) -> CaseRecord:
    record = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    return record


@router.post("/run")
def run(
    case_id: str,
    payload: InvestigationRunRequest,
    user: dict = Depends(require_role("investigator", "admin")),
    db: Session = Depends(get_db),
):
    """
    Executes the full happy path:
    wallet -> transactions -> graph -> suspicious path -> risk -> VASP
    hypothesis, then stores a snapshot for the report/evidence screens.
    """
    case = _get_case_or_404(case_id, db)

    cache_key = f"investigation:{case.suspect_wallet}:{payload.tx_limit}"

    def _compute():
        try:
            result = run_investigation(case.suspect_wallet, _provider, payload.tx_limit)
        except ProviderUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Blockchain provider unavailable: {exc}. No fabricated "
                "data was returned.",
            )
        return result.to_dict()

    result_dict = cached_json(cache_key, ttl_seconds=300, producer=_compute)

    run_record = InvestigationRun(
        id=str(uuid.uuid4()),
        case_id=case.id,
        result_json=result_dict,
        risk_score=result_dict["wallet_risk"]["risk_score"],
        risk_level=result_dict["wallet_risk"]["risk_level"],
    )
    db.add(run_record)
    db.commit()

    return result_dict


@router.get("/latest")
def latest(
    case_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(case_id, db)
    run_record = (
        db.query(InvestigationRun)
        .filter(InvestigationRun.case_id == case.id)
        .order_by(InvestigationRun.generated_at.desc())
        .first()
    )
    if not run_record:
        raise HTTPException(
            status_code=404,
            detail="No investigation has been run for this case yet. POST to "
            "/run first.",
        )
    return run_record.result_json
