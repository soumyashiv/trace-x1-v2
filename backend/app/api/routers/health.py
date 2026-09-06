from __future__ import annotations

from fastapi import APIRouter

from app.api.cache import is_cache_healthy
from app.api.schemas import SystemHealth
from app.core.provider import EVMBlockchainProvider, MockBlockchainProvider
from app.db.session import engine

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=SystemHealth)
def health():
    mock = MockBlockchainProvider()
    evm = EVMBlockchainProvider()

    db_ok = True
    try:
        with engine.connect():
            pass
    except Exception:
        db_ok = False

    return SystemHealth(
        api=True,
        mock_provider=mock.is_healthy(),
        evm_provider_configured=bool(evm._rpc_url and evm._explorer_api_key),
        evm_provider_healthy=evm.is_healthy(),
        database=db_ok,
        cache=is_cache_healthy(),
    )
