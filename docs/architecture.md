# Architecture

```
                    ┌─────────────────────┐
                    │   Next.js Frontend   │
                    │  (React, TypeScript) │
                    └──────────┬───────────┘
                               │ REST (JSON) over HTTPS
                    ┌──────────▼───────────┐
                    │      FastAPI App      │
                    │  auth / cases / runs  │
                    │  reports / health      │
                    └───┬───────────────┬───┘
             ┌──────────┘               └───────────┐
   ┌─────────▼─────────┐                 ┌───────────▼───────────┐
   │   Case Service      │                 │   Investigation        │
   │ (Postgres via SQLA) │                 │   Pipeline (core/)      │
   └──────────────────────┘                 │                        │
                                             │ Graph Service (NetworkX)│
                                             │ Risk Service (explainable│
                                             │  feature scoring)        │
                                             │ VASP Attribution Service │
                                             │ Report Service (PDF/     │
                                             │  JSON/CSV via reportlab) │
                                             └───────────┬────────────┘
                                                          │
                                             ┌────────────▼────────────┐
                                             │ BlockchainProvider (ABC)  │
                                             │  ├─ MockBlockchainProvider│
                                             │  └─ EVMBlockchainProvider │
                                             └────────────┬────────────┘
                                                          │
                                             ┌────────────▼────────────┐
                                             │ Redis (cache + rate limit)│
                                             └───────────────────────────┘
```

## Why the provider abstraction matters

Every analytics service (graph, risk, VASP attribution) depends only on
the `BlockchainProvider` interface, never on a concrete chain client. This
means:

- The demo runs fully offline via `MockBlockchainProvider`, which
  deterministically synthesizes the same wallet graph for the same
  address every time (see `app/core/provider.py`).
- A real `EVMBlockchainProvider` can be swapped in without touching
  `graph_service.py`, `risk_service.py`, or `vasp_service.py`.
- If the real provider's credentials are missing or the upstream API is
  down, it raises `ProviderUnavailableError` instead of silently
  returning empty or fabricated data — callers must handle that
  explicitly (the API layer turns it into an HTTP 503 with a clear
  message, never a fake result).

## Request flow for the happy path

1. `POST /cases` — investigator creates a case with a victim-reported wallet.
2. `POST /cases/{id}/investigation/run` — triggers `app.core.pipeline.run_investigation`:
   - pulls transactions through the provider (cached in Redis per address/TTL)
   - builds a `networkx.MultiDiGraph`
   - detects intermediaries and candidate suspicious paths to labelled nodes
   - computes an explainable risk score for the suspect wallet and every intermediary
   - computes evidence-backed VASP attribution hypotheses
   - persists a snapshot (`InvestigationRun`) to Postgres
3. `GET /cases/{id}/investigation/latest` — frontend renders the graph, risk, and VASP tabs from the stored snapshot.
4. `GET /cases/{id}/report.{json,csv,pdf}` — regenerates a fresh report from the same core objects.

## Layering rules

- `app/core/*` has **no FastAPI/SQLAlchemy import**. It is pure Python +
  NetworkX + reportlab, so it can be unit-tested with nothing but the
  standard library (see `backend/tests/`) and reused outside the API
  (CLI, notebook, batch job) unchanged.
- `app/api/*` is a thin HTTP layer: auth, request/response schemas,
  routing, caching, rate limiting. It calls into `app/core/*` and never
  duplicates its logic.
- `app/db/*` is persistence only: case records and investigation-run
  snapshots. Raw transaction data is not persisted verbatim — it's
  re-derived through the provider (with caching), keeping the DB small
  and avoiding a second source of truth that could drift from the chain.
