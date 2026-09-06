# Demo Instructions (fully offline)

The entire demo runs on `MockBlockchainProvider` — no internet access or
API keys required.

## 1. Start the stack

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste into .env as TRACEX_JWT_SECRET
docker compose up --build
```

## 2. Log in

Open http://localhost:3000 → redirected to `/login`.
- username: `demo.investigator`
- password: `ChangeMe123!`

## 3. Create an investigation

Go to **New Investigation**. Use one of the two built-in demo wallets:
- `0xVICTIM0000000000000000000000000000A1`
- `0xVICTIM0000000000000000000000000000B2`

Give it a title (e.g. "Reported crypto investment scam") and submit. This
creates the case and immediately runs the full pipeline.

## 4. Walk through the screens

You'll land on the case detail page with tabs:

1. **Transaction Graph** — the victim wallet, a burner wallet, two
   intermediaries, and a known exchange cluster node. Click any node to
   see its wallet-level risk detail and evidence. The graph is generated
   deterministically, so this always looks the same for the same wallet.
2. **Risk Analysis** — per-wallet risk scores with a full feature
   contribution breakdown. Note the suspect (victim) wallet itself scores
   *low* — it's the source of the funds, not a laundering node — while
   the burner and intermediary wallets score higher due to fast
   pass-through behavior (see the "velocity" and "routing_irregularity"
   contributions).
3. **VASP Attribution** — shows the hypothesis that funds reached
   "Krakenish Exchange (mock)", with supporting evidence, a confidence
   score under 100%, and the standard hedging disclaimer.
4. **Evidence** — the flat evidence list backing the suspect wallet's score.
5. **Timeline** — every transfer, sorted chronologically.
6. **Report** — download the same investigation as PDF, JSON, or CSV.

## 5. Re-run the trace

The "Re-run trace" button re-executes the pipeline (cached for 5 minutes
per wallet+limit in Redis, so a second click within that window is fast).

## 6. Check system health

Go to **Settings** to see live status of the API, mock provider, database,
and cache — and an explicit statement of which data sources are mocked.

## What to point out in a live demo

- The mock provider is deterministic: the same wallet always produces the
  same graph, so panics about "the demo might show something different
  this time" don't apply.
- Every risk score comes with a feature breakdown — there is no code path
  that returns a bare number.
- Every VASP attribution carries a confidence < 100% and a disclaimer —
  the system is designed to never claim certainty it doesn't have.
- The provider abstraction (`BlockchainProvider`) is what lets this same
  UI and pipeline run against a real Ethereum RPC later by only changing
  environment variables, not code.
