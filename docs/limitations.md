# Limitations

This is an MVP built for the SIH26183 problem statement. It is honest
about what it does and does not do. Please read this before treating any
output as a finished investigative product.

## Data source

- The default and demo-safe data source is **`MockBlockchainProvider`**,
  which deterministically **synthesizes** a wallet graph — it is not real
  blockchain data. It exists so the product can be evaluated fully
  offline and reproducibly.
- **`EVMBlockchainProvider`** is implemented and will fetch real
  Ethereum-compatible transaction history via an RPC endpoint + explorer
  API, but only if `TRACEX_EVM_RPC_URL` and `TRACEX_EXPLORER_API_KEY` are
  configured. It has not been load-tested against real high-volume
  wallets in this build. Bitcoin/UTXO chains and Tron are represented in
  the data model (`Chain` enum) but have no working provider implementation yet.

## Government integrations

- `NcrpConnector` and `SahyogConnector` (see `app/core/integrations.py`)
  are **mock connectors only**. No live NCRP or SAHYOG API access,
  credentials, or data-sharing agreement exists for this prototype.
  Do not present their output as real government data in a demo without
  saying so explicitly.

## Risk scoring

- The risk engine is a **transparent, hand-weighted feature model**, not
  a trained classifier. The feature weights in `risk_service.WEIGHTS` are
  reasoned defaults, not fit to labelled ground-truth fraud cases (none
  were available for this prototype). Treat risk scores as investigative
  triage signals, not certainty.
- No XGBoost/LightGBM model is trained or shipped in this MVP, despite
  being named in the target tech stack — see `docs/roadmap.md` for why,
  and what would be required to add one responsibly (a labelled dataset
  plus a SHAP-style explanation layer, to preserve the "never an
  unexplained score" requirement).

## VASP attribution

- Attribution is based entirely on a **small mock label/cluster
  database** (`_MOCK_LABEL_DB` in `provider.py`) with two entries. A real
  deployment needs a maintained, evidence-backed label database (exchange
  disclosures, sanctions lists, clustering heuristics) — this is
  explicitly out of scope here.
- Attribution is never reported as guaranteed; every result includes a
  confidence score, supporting/contradicting evidence, and a disclaimer.
  Confidence intentionally decays with hop distance and drops sharply
  when a path crosses a wallet labelled as a mixer.

## Tracing completeness

- The pipeline does **not** claim to trace funds through unresolved
  mixers, privacy coins, or cross-chain bridges. Where a path crosses such
  a node, this is surfaced as reduced confidence, not silently ignored.
- Graph expansion in `pipeline.run_investigation` is bounded (2 rounds of
  BFS expansion in this MVP) for demo performance. Production tracing
  needs a budgeted, resumable crawl with pagination against a real
  indexer — see roadmap.

## Security

- Demo user credentials (`demo.investigator` / `ChangeMe123!`) are for
  local evaluation only and must be replaced before any real deployment.
- `TRACEX_JWT_SECRET` has no default — the app refuses to start without
  one being set, precisely so a real secret is never accidentally skipped.
- Role model is minimal (`investigator` / `admin`). No per-case access
  control (e.g. limiting an investigator to only their assigned cases) is
  implemented yet.
- Rate limiting is a simple fixed-window counter in Redis; it fails open
  if Redis is unreachable (availability prioritized over strict limiting
  in that failure mode — reconsider for a production threat model).

## Testing

- Core analytics (`app/core/*`) has real unit + integration test coverage
  run with `unittest`/`pytest` and no external services required.
- The FastAPI HTTP layer has a written end-to-end test
  (`tests/test_api_happy_path.py`) that requires the full dependency set
  and a running Postgres/Redis — it was not executed in the offline
  sandbox this project was authored in. Run it yourself via
  `docker compose up` + `pytest` before relying on it (see README).
- No frontend automated tests are included in this MVP; the described
  screens are implemented but only manually smoke-testable via `npm run dev`.
