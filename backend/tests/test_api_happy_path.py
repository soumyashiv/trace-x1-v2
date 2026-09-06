"""
End-to-end API test for the full happy path over HTTP:

    login -> create case -> run investigation -> fetch graph/risk/vasp
          -> export report (json/csv/pdf)

Requires the full dependency set (fastapi, httpx, sqlalchemy, etc. — see
requirements.txt) and a reachable Postgres + Redis (docker-compose spins
both up). Not run in the stdlib-only sandbox used to build this project;
run it with:

    docker compose up -d db redis
    export TRACEX_DATABASE_URL=postgresql+psycopg2://tracex:tracex@localhost:5432/tracex
    export TRACEX_REDIS_URL=redis://localhost:6379/0
    export TRACEX_JWT_SECRET=test-secret-do-not-use-in-prod
    pytest backend/tests/test_api_happy_path.py -v
"""
import os

os.environ.setdefault("TRACEX_JWT_SECRET", "test-secret-do-not-use-in-prod")

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    resp = client.post(
        "/auth/login", json={"username": "demo.investigator", "password": "ChangeMe123!"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_rejects_bad_credentials():
    resp = client.post("/auth/login", json={"username": "demo.investigator", "password": "wrong"})
    assert resp.status_code == 401


def test_full_happy_path(auth_headers):
    # 1. create a case
    resp = client.post(
        "/cases",
        json={
            "title": "Reported scam wallet",
            "suspect_wallet": "0xVICTIM0000000000000000000000000000A1",
            "chain": "MOCK",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    case_id = resp.json()["case_id"]

    # 2. run the investigation pipeline
    resp = client.post(
        f"/cases/{case_id}/investigation/run", json={"tx_limit": 500}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["transaction_count"] > 0
    assert "wallet_risk" in result
    assert "vasp_attributions" in result

    # 3. fetch the latest snapshot
    resp = client.get(f"/cases/{case_id}/investigation/latest", headers=auth_headers)
    assert resp.status_code == 200

    # 4. export reports in all three formats
    resp = client.get(f"/cases/{case_id}/report.json", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")

    resp = client.get(f"/cases/{case_id}/report.csv", headers=auth_headers)
    assert resp.status_code == 200
    assert "tx_hash" in resp.text

    resp = client.get(f"/cases/{case_id}/report.pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_health_endpoint_is_public_and_reports_status():
    resp = client.get("/system/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mock_provider"] is True
