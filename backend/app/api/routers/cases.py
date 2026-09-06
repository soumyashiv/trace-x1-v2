from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_role
from app.api.schemas import CaseCreateRequest, CaseSummary
from app.db.models import CaseRecord
from app.db.session import get_db

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseSummary)
def create_case(
    payload: CaseCreateRequest,
    user: dict = Depends(require_role("investigator", "admin")),
    db: Session = Depends(get_db),
):
    record = CaseRecord(
        id=str(uuid.uuid4()),
        title=payload.title,
        investigator_username=user["username"],
        suspect_wallet=payload.suspect_wallet,
        chain=payload.chain,
        notes=payload.notes,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return CaseSummary(
        case_id=record.id,
        title=record.title,
        investigator=record.investigator_username,
        suspect_wallet=record.suspect_wallet,
        chain=record.chain,
        status=record.status,
        created_at=record.created_at,
    )


@router.get("", response_model=list[CaseSummary])
def list_cases(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = db.query(CaseRecord).order_by(CaseRecord.created_at.desc()).all()
    return [
        CaseSummary(
            case_id=r.id,
            title=r.title,
            investigator=r.investigator_username,
            suspect_wallet=r.suspect_wallet,
            chain=r.chain,
            status=r.status,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.get("/{case_id}", response_model=CaseSummary)
def get_case(
    case_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseSummary(
        case_id=record.id,
        title=record.title,
        investigator=record.investigator_username,
        suspect_wallet=record.suspect_wallet,
        chain=record.chain,
        status=record.status,
        created_at=record.created_at,
    )
