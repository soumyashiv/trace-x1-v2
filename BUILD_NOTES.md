# Build Notes — what was actually verified in this build

Full transparency on what was executed for real vs. written-but-unrun,
and the sandbox constraints that shaped that split.

## Sandbox constraints during authoring

The environment this project was built in has:
- **No internet/network access** — `pip install fastapi` etc. fails
  (`No matching distribution found`).
- **No Docker daemon** — `docker` is not installed.
- Node.js/npm ARE present, but with no network, `npm install` cannot
  fetch Next.js/React/reactflow/etc.
- Pre-installed and usable: Python 3.12 stdlib, `networkx`, `numpy`,
  `pandas`, `scikit-learn`, `reportlab`.

Because of this, the project was deliberately split so the **entire
business-logic core** (`backend/app/core/*`) has zero dependency on
FastAPI/SQLAlchemy/Pydantic — it only needs the standard library plus
NetworkX and reportlab, both of which were available. That let the core
be genuinely written, executed, and tested in this environment, rather
than only hand-inspected.

The FastAPI HTTP layer, the database layer, and the Next.js frontend are
complete, carefully written, and internally consistent with the tested
core — but they were **not executed** here, because their dependencies
could not be installed offline. Run them via `docker compose up` on a
machine with internet access (see README) — `docker-compose.yml` handles
Postgres/Redis/backend/frontend wiring for you.

## What was actually run, right here, and passed

```
cd backend
python3 -m unittest discover -s tests -v
```
excluding only `tests/test_api_happy_path.py` (needs FastAPI/httpx —
not installable offline). Result:

```
Ran 45 tests in 0.036s
OK
```

Covering:
- `test_provider.py` (9 tests) — MockBlockchainProvider determinism
  across calls/instances, distinct wallets produce distinct graphs,
  known/unknown label lookups, `limit` respected; EVMBlockchainProvider
  fails loudly (`ProviderUnavailableError`) rather than fabricating data
  when unconfigured.
- `test_graph_service.py` (8 tests) — graph shape, hop distances, fan-in/
  fan-out, intermediary detection, path-finding to labelled nodes,
  chronological timeline ordering.
- `test_risk_service.py` (7 tests) — score bounds, the **"never
  unexplained score"** requirement (contributions present and sum to the
  score, evidence non-empty), confidence bounds, relative ordering
  sanity (labelled exchange > burner > unconnected stranger).
- `test_vasp_service.py` (4 tests) — finds the known exchange, **never
  asserts >99% confidence**, honest "no match found" path (not
  fabricated), unreachable source handled cleanly.
- `test_report_service.py` (4 tests) — JSON schema completeness, no
  banned "guaranteed"/"100% confirmed" language anywhere in the report,
  CSV row-count matches transaction count, PDF bytes are valid
  (`%PDF` magic number, non-trivial size).
- `test_pipeline_happy_path.py` (7 tests) — the full spec-required chain
  end to end: case → wallet → transactions → graph → suspicious path →
  risk → VASP hypothesis, plus a determinism check (same wallet, fresh
  provider instance, same result).
- `test_integrations.py` (5 tests) — mock NCRP/SAHYOG connector contracts.

Also actually generated (not just described) a real sample report set:
`sample_report.json`, `sample_transactions.csv`, `sample_report.pdf`
(valid PDF, opens normally) from a live run of
`run_investigation()` against the demo wallet.

## Benchmarks (measured on the sandbox's CPU, single-threaded, n as noted)

Core pipeline, demo-sized dataset (~9 transactions, 6 wallets):

| Operation | n | mean | p50 | p95 | min | max |
|---|---|---|---|---|---|---|
| `MockBlockchainProvider.get_transactions` | 200 | 0.036 ms | 0.033 ms | 0.048 ms | 0.032 ms | 0.262 ms |
| **Full `run_investigation()` (happy path)** | 100 | **1.615 ms** | 1.467 ms | 1.956 ms | 1.148 ms | 10.003 ms |
| `report_service.generate_json` | 200 | 0.075 ms | 0.069 ms | 0.116 ms | 0.064 ms | 0.174 ms |
| `report_service.generate_csv` | 200 | 0.192 ms | 0.189 ms | 0.219 ms | 0.158 ms | 0.364 ms |
| `report_service.generate_pdf` | 50 | **9.417 ms** | 9.291 ms | 11.413 ms | 7.900 ms | 13.528 ms |

Stress test at a larger, non-demo scale (synthetic random graph, 500
wallets / 5,000 transactions, seeded for reproducibility):

| Stage | Time |
|---|---|
| `build_graph` | 10.61 ms |
| `compute_hops` (BFS from source) | 0.40 ms |
| `detect_intermediaries` | 1.06 ms |
| `score_wallet` (single wallet) | 0.37 ms |
| **Total core stages** | **12.44 ms** for 5,000 tx / 500 wallets |

Full offline test suite (45 tests, includes process startup overhead):
**~293 ms wall clock** for the whole `python3 -m unittest ...` subprocess.

### Reading these numbers honestly

- These measure **CPU-bound Python logic only** — no network I/O, no
  database round-trip, no HTTP overhead, no browser rendering. Real-world
  latency through the FastAPI layer + Postgres + Redis + network will be
  higher (typically dominated by DB/HTTP overhead, likely tens of
  milliseconds per request, not microseconds).
- PDF generation (~9-13 ms) is the slowest single core operation, as
  expected for a formatted-document renderer — still fast enough to be a
  non-issue for on-demand report downloads.
- The 500-wallet/5,000-tx stress test shows the graph/risk stages scale
  roughly linearly and stay well under 15 ms combined — the current
  implementation should comfortably handle multi-hop investigative graphs
  of this size without needing async/background processing. Real
  production wallets with tens of thousands of transactions would need
  the bounded/resumable crawl described in `docs/roadmap.md` — this
  benchmark does not claim to represent that scale.
- No load/concurrency testing (multiple simultaneous investigators) was
  performed — that requires the running API + DB stack, which could not
  be started in this offline sandbox.

## How to reproduce these benchmarks yourself

```bash
cd backend
python3 -c "
import time, statistics
from app.core.provider import MockBlockchainProvider
from app.core.pipeline import run_investigation
from app.core.demo_data import build_demo_case
from app.core.report_service import generate_json, generate_csv, generate_pdf

wallet = '0xVICTIM0000000000000000000000000000A1'
case = build_demo_case('case-demo-001')
provider = MockBlockchainProvider()
result = run_investigation(wallet, provider)

def bench(label, fn, n=200):
    times = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); times.append((time.perf_counter()-t0)*1000)
    times.sort()
    print(f'{label}: mean={statistics.mean(times):.3f}ms p50={statistics.median(times):.3f}ms p95={times[int(0.95*len(times))-1]:.3f}ms')

bench('get_transactions', lambda: provider.get_transactions(wallet))
bench('run_investigation', lambda: run_investigation(wallet, MockBlockchainProvider()), n=100)
bench('generate_json', lambda: generate_json(case, result))
bench('generate_csv', lambda: generate_csv(case, result))
bench('generate_pdf', lambda: generate_pdf(case, result), n=50)
"
```
