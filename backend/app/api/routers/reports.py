from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.demo_data import build_demo_case
from app.core.models import Case, Chain
from app.core.pipeline import run_investigation
from app.core.provider import MockBlockchainProvider
from app.core.report_service import generate_csv, generate_json, generate_pdf
from app.db.models import CaseRecord, InvestigationRun
from app.db.session import get_db

router = APIRouter(prefix="/cases/{case_id}/report", tags=["reports"])
_provider = MockBlockchainProvider()


def _load_case_and_result(case_id: str, db: Session):
    case_record = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
    if not case_record:
        raise HTTPException(status_code=404, detail="Case not found")

    run_record = (
        db.query(InvestigationRun)
        .filter(InvestigationRun.case_id == case_id)
        .order_by(InvestigationRun.generated_at.desc())
        .first()
    )
    if not run_record:
        raise HTTPException(
            status_code=409,
            detail="No investigation run found for this case. Run the "
            "investigation before requesting a report.",
        )

    case = Case(
        case_id=case_record.id,
        title=case_record.title,
        investigator=case_record.investigator_username,
        suspect_wallet=case_record.suspect_wallet,
        chain=Chain(case_record.chain) if case_record.chain in Chain.__members__ else Chain.MOCK,
        created_at=case_record.created_at,
        status=case_record.status,
        notes=case_record.notes,
    )
    # Recompute the full result object (graph/paths/etc.) fresh from the
    # provider so exports always reflect an InvestigationResult instance,
    # not just the cached dict snapshot.
    result = run_investigation(case.suspect_wallet, _provider)
    return case, result


@router.get(".json")
def report_json(case_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    case, result = _load_case_and_result(case_id, db)
    return Response(content=generate_json(case, result), media_type="application/json")


@router.get(".csv")
def report_csv(case_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    case, result = _load_case_and_result(case_id, db)
    return Response(
        content=generate_csv(case, result),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{case_id}_transactions.csv"'},
    )


@router.get(".pdf")
def report_pdf(case_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    case, result = _load_case_and_result(case_id, db)
    pdf_bytes = generate_pdf(case, result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{case_id}_report.pdf"'},
    )
