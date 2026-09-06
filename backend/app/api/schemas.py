from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    suspect_wallet: str = Field(..., min_length=6, max_length=128)
    chain: str = Field(default="MOCK")
    notes: str = ""


class CaseSummary(BaseModel):
    case_id: str
    title: str
    investigator: str
    suspect_wallet: str
    chain: str
    status: str
    created_at: datetime


class InvestigationRunRequest(BaseModel):
    tx_limit: int = Field(default=500, ge=1, le=5000)


class SystemHealth(BaseModel):
    api: bool
    mock_provider: bool
    evm_provider_configured: bool
    evm_provider_healthy: bool
    database: bool
    cache: bool
