"""
SQLAlchemy models for persisted case data.

Note: raw transaction/graph data is intentionally NOT persisted verbatim
in Postgres for the MVP — it is re-fetched through the provider
abstraction (and cached in Redis) on demand. What IS persisted is the
case record and a snapshot of each completed investigation run, which is
what the report and audit-log screens read from.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="investigator")
    created_at = Column(DateTime, default=datetime.utcnow)


class CaseRecord(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    investigator_username = Column(String, ForeignKey("users.username"), nullable=False)
    suspect_wallet = Column(String, nullable=False, index=True)
    chain = Column(String, nullable=False, default="MOCK")
    status = Column(String, nullable=False, default="open")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    investigation_runs = relationship(
        "InvestigationRun", back_populates="case", cascade="all, delete-orphan"
    )


class InvestigationRun(Base):
    """A snapshot of one completed pipeline execution for a case, so the
    report and evidence screens don't need to re-run the pipeline (and so
    an investigator can compare runs over time as new tx data arrives)."""

    __tablename__ = "investigation_runs"

    id = Column(String, primary_key=True, default=_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    result_json = Column(JSON, nullable=False)   # InvestigationResult.to_dict()
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("CaseRecord", back_populates="investigation_runs")


class AuditLogEntry(Base):
    """Every sensitive action (login, case creation, investigation run,
    report export) is written here for accountability. Logging is
    privacy-conscious: full wallet addresses are fine to log (they are
    public blockchain data), but request bodies containing victim PII
    (name, phone, etc., if ever added) must never be logged verbatim."""

    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    detail = Column(Text, default="")
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
