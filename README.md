# TRACE-X — SIH26183

Real-time identification of fraud-linked cryptocurrency exchanges from
victim-reported suspect wallet addresses, through automated blockchain
analytics.

This repo implements the **end-to-end happy path** first, as instructed
by the brief:

```
case -> wallet -> transactions -> graph -> suspicious path -> risk
     -> VASP hypothesis -> report
```

then layers the remaining screens, security, and performance features on
top of that verified core. See `docs/limitations.md` for a precise,
honest account of what is real vs. mocked in this build, and
`BUILD_NOTES.md` for how this was actually built/tested and what you need
to do to run it yourself.

## Stack

- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy, NetworkX, reportlab
- **Data**: PostgreSQL, Redis
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, React Flow
- **Infra**: Docker Compose

## Quickstart (Docker — recommended)

```bash
cp .env.example .env
# generate a real secret and paste it into .env as TRACEX_JWT_SECRET:
python3 -c "import secrets; print(secrets.token_hex(32))"

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API + docs: http://localhost:8000/docs

Log in with the demo investigator account:
- username: `demo.investigator`
- password: `ChangeMe123!`

## Quickstart (without Docker)

Backend:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TRACEX_JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export TRACEX_DATABASE_URL=sqlite:///./tracex.db   # simplest local option, no Postgres needed
uvicorn app.api.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Running the tests

Core analytics (no external services needed — pure stdlib + NetworkX/reportlab):
```bash
cd backend
python3 -m unittest discover -s tests -v
```
This runs 45 tests covering the provider abstraction, graph construction,
risk scoring, VASP attribution, report generation, the full happy-path
integration, and the mock NCRP/SAHYOG connectors. **All 45 pass** — this
was verified for real while building this project (see `BUILD_NOTES.md`).

Full API test (needs the dependency set + Postgres/Redis reachable):
```bash
docker compose up -d db redis
pip install -r backend/requirements.txt
export TRACEX_JWT_SECRET=test-secret-do-not-use-in-prod
export TRACEX_DATABASE_URL=postgresql+psycopg2://tracex:tracex@localhost:5432/tracex
export TRACEX_REDIS_URL=redis://localhost:6379/0
pytest backend/tests/test_api_happy_path.py -v
```

## Demo walkthrough

See `docs/demo_instructions.md`.

## Documentation index

- `docs/architecture.md` — system design and the provider-abstraction rationale
- `docs/api.md` — endpoint reference
- `docs/schema.md` — database schema
- `docs/limitations.md` — what's real, what's mocked, what's not implemented
- `docs/roadmap.md` — what comes after the MVP
- `docs/demo_instructions.md` — step-by-step offline demo script
- `BUILD_NOTES.md` — how this specific build was authored, tested, and benchmarked
