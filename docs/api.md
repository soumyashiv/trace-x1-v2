# API Reference

Interactive OpenAPI docs are also served at `/docs` (Swagger UI) and
`/redoc` once the backend is running.

Base URL (local): `http://localhost:8000`

## Auth

### `POST /auth/login`
```json
{ "username": "demo.investigator", "password": "ChangeMe123!" }
```
→ `{ "access_token": "...", "token_type": "bearer", "role": "investigator" }`

Send the token on every subsequent request:
`Authorization: Bearer <access_token>`

Demo users (see `app/api/auth.py` — replace before any real deployment):
| username | password | role |
|---|---|---|
| demo.investigator | ChangeMe123! | investigator |
| demo.admin | ChangeMeAdmin123! | admin |

## Cases

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/cases` | investigator, admin | Create a case from a victim-reported wallet |
| GET | `/cases` | any authenticated | List all cases |
| GET | `/cases/{case_id}` | any authenticated | Get one case |

`POST /cases` body:
```json
{ "title": "Reported scam", "suspect_wallet": "0xVICTIM...", "chain": "MOCK", "notes": "" }
```

## Investigation pipeline

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/cases/{case_id}/investigation/run` | investigator, admin | Runs the full happy-path pipeline |
| GET | `/cases/{case_id}/investigation/latest` | any authenticated | Returns the most recent snapshot |

`POST .../run` body: `{ "tx_limit": 500 }`

Response shape (`InvestigationResult.to_dict()`):
```json
{
  "suspect_wallet": "...",
  "transaction_count": 8,
  "intermediaries": ["0xBURNER_...", "0xINTER1_..."],
  "suspicious_paths": [["0xVICTIM...", "0xBURNER_...", "...", "0xEXCHANGE_..."]],
  "wallet_risk": {
    "address": "...", "risk_score": 23.8, "risk_level": "low",
    "feature_contributions": { "...": 0.0 }, "raw_features": { "...": 0.0 },
    "evidence": ["..."], "confidence": 0.4
  },
  "intermediary_risks": [ ... ],
  "vasp_attributions": [
    {
      "target_address": "0xEXCHANGE_KRAKENISH_HOT1",
      "likely_entity": "Krakenish Exchange (mock)",
      "confidence": 0.58,
      "supporting_evidence": ["..."],
      "contradicting_evidence": [],
      "last_verified": "2026-08-01T00:00:00",
      "source": "mock_vasp_registry_v1",
      "disclaimer": "This is an evidence-based hypothesis, not a confirmed identification..."
    }
  ],
  "timeline": [ { "tx_hash": "...", "from": "...", "to": "...", "value": 1234.5, "timestamp": "..." } ],
  "generated_at": "...",
  "summary": "Suspect wallet ... shows a low-risk fund flow (23.8/100) with a 58% confidence hypothesis..."
}
```

## Reports

| Method | Path | Description |
|---|---|---|
| GET | `/cases/{case_id}/report.json` | Full structured report |
| GET | `/cases/{case_id}/report.csv` | Raw transaction ledger |
| GET | `/cases/{case_id}/report.pdf` | Formatted investigation report |

Requires at least one successful `POST .../investigation/run` first
(returns `409` otherwise).

## System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/system/health` | none | Liveness of API, mock/EVM providers, DB, cache |

## Errors

Standard FastAPI/Pydantic validation errors (`422`) for malformed bodies.
`401` for missing/invalid tokens, `403` for role mismatch, `404` for
unknown case IDs, `409` when a report is requested before any
investigation has run, `429` when the per-IP/per-user rate limit is
exceeded, `503` when a real blockchain provider is configured but
unreachable (never silently substituted with fake data).
