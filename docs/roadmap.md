# Roadmap

Ordered roughly by what unlocks the most value next.

## 1. Real chain coverage
- Harden `EVMBlockchainProvider` against rate limits/pagination for
  high-activity wallets; add retry/backoff.
- Add a Bitcoin/UTXO provider (clustering is fundamentally different —
  common-input-ownership heuristic needed for wallet clustering).
- Add a Tron provider (high relevance for USDT-based scam flows).

## 2. Trained, explainable risk model
- Collect/obtain a labelled dataset of confirmed fraud vs. benign wallets.
- Train a gradient-boosted model (XGBoost/LightGBM) on the same feature
  set already computed in `risk_service.py`.
- Add a SHAP explanation layer so the trained model still satisfies
  "never return an unexplained risk score" — this is a hard requirement,
  not a nice-to-have, so the model should not ship without it.
- A/B the trained model against the current weighted-feature baseline
  before fully replacing it.

## 3. Real label/cluster database
- Ingest exchange-published hot-wallet disclosures, sanctions lists
  (OFAC SDN, etc.), and community-maintained scam databases.
- Add proper clustering (change-address heuristics, multi-input
  clustering) instead of relying solely on direct address labels.
- Add label provenance versioning so `last_verified` is real, not fixed.

## 4. Credentialed government integrations
- Formal data-sharing agreement + credentials for NCRP.
- Replace `MockNcrpConnector`/`MockSahyogConnector` with real
  implementations behind the same interface — no calling code should
  need to change.

## 5. Graph scale & performance
- Replace the bounded 2-round BFS expansion with a budgeted, resumable
  crawl (max nodes/edges, background job with progress reporting).
- Move large per-case graphs out of the `investigation_runs.result_json`
  blob and into a proper graph store (Neo4j or pg with recursive CTEs) if
  case sizes grow beyond a few thousand nodes.

## 6. Access control & compliance
- Per-case assignment and access control (investigators see only their
  cases unless admin).
- Full audit trail UI reading from `audit_log`.
- Formal data retention policy for victim-reported wallet data.

## 7. Frontend depth
- Automated frontend tests (component + Playwright E2E for the happy path).
- Path-highlighting and time-scrubber on the transaction graph.
- Multi-case correlation view (shared intermediary wallets across cases).
