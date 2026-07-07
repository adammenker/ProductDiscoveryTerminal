# Product Discovery Terminal

A local-first MVP for discovering consumer product opportunities before committing capital.

The app runs a scheduled-batch style intelligence loop:

```text
ingestion plugins -> raw observations -> normalization -> analyzer plugins -> scoring -> terminal UI
```

The first version uses only manual/mock plugins. There are no real external API calls, no event-driven cloud infrastructure, and no downstream FBA/listing/order automation.

## Run Locally

```bash
docker compose up --build
```

Services:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Health: <http://localhost:8000/health>
- Postgres: `localhost:5432`

Open the frontend and press **Run Pipeline** to load mock/manual evidence, normalize products, run analyzers, and generate scores.

## Environment

Copy the example environment file for local secrets:

```bash
cp .env.example .env
```

`docker-compose.yml` passes `.env` into the backend container when present. Keep `.env` local; it is ignored by git.

### Etsy Open API

The `etsy_api` ingestion plugin is installed but disabled by default while app approval is pending.

Required local values:

```bash
ETSY_API_ENABLED=false
ETSY_API_KEYSTRING=your_etsy_keystring
ETSY_SHARED_SECRET=your_etsy_shared_secret
ETSY_API_BASE_URL=https://openapi.etsy.com/v3/application
```

After Etsy approves the app, set `ETSY_API_ENABLED=true`, restart the backend, and run the plugin explicitly with a keyword query:

```bash
curl -X POST http://localhost:8000/ingestion/run \
  -H 'Content-Type: application/json' \
  -d '{"plugins":["etsy_api"],"query":{"query":"ice roller","limit":25}}'
```

The default pipeline still runs only mock/manual plugins so local development remains stable.

## Backend Development

```bash
cd backend
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m ruff check app
```

The backend defaults to a local SQLite database when `DATABASE_URL` is not set. Docker Compose uses Postgres and runs Alembic migrations at startup.

## Frontend Development

```bash
cd frontend
pnpm install
pnpm dev
pnpm typecheck
pnpm build
```

If running outside Docker, set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` when the backend is on the default port.

## Plugin Model

Ingestion plugins live under:

```text
backend/app/plugins/ingestion/
```

Analyzer plugins live under:

```text
backend/app/plugins/analyzers/
```

To add an MVP ingestion plugin:

1. Implement `fetch(query: IngestionQuery) -> list[RawObservationDTO]`.
2. Keep source-specific parsing inside the plugin folder.
3. Register the plugin in `backend/app/plugins/registry.py`.
4. Add isolated plugin tests.

Core services should only know about observations, products, signals, insights, scores, and plugin contracts.

## Implemented MVP

- FastAPI backend with SQLAlchemy models and Alembic migration.
- Postgres through Docker Compose, SQLite-compatible local tests.
- Manual CSV, Amazon mock, Alibaba mock, Reddit mock, Google Trends mock, and opt-in Etsy API ingestion plugins.
- Demand, competition, supplier, economics, risk, and review analyzer plugins.
- Content-hash observation deduplication.
- Simple alias-based product normalization.
- Versioned, explainable scoring engine.
- REST endpoints for products, opportunities, plugins, plugin runs, health, and pipeline trigger.
- Next.js terminal UI for dashboard, search, product detail, plugins, and run history.
