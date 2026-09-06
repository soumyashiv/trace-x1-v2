from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.auth import authenticate, create_access_token
from app.api.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    role = authenticate(payload.username, payload.password)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token(subject=payload.username, role=role)
    return LoginResponse(access_token=token, role=role)
