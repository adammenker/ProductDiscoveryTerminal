# Product Discovery Terminal

A local-first MVP for discovering consumer product opportunities before committing capital.

The app runs a scheduled-batch style intelligence loop:

```text
ingestion plugins -> raw observations -> normalization -> analyzer plugins -> scoring -> terminal UI
```

The default pipeline uses only manual/mock plugins. Real API plugins are opt-in and disabled until credentials are configured. There is no event-driven cloud infrastructure and no downstream FBA/listing/order automation.

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

### Alibaba.com Open API

The `alibaba_open_api` ingestion plugin is installed but disabled by default while Alibaba app/API access is pending.

Required local values:

```bash
ALIBABA_API_ENABLED=false
ALIBABA_APP_KEY=your_alibaba_app_key
ALIBABA_APP_SECRET=your_alibaba_app_secret
ALIBABA_ACCESS_TOKEN=your_alibaba_access_token
ALIBABA_PRODUCT_SEARCH_URL=
```

After Alibaba approval confirms the product/supplier search API route, fill `ALIBABA_PRODUCT_SEARCH_URL`, set `ALIBABA_API_ENABLED=true`, restart the backend, and run the plugin explicitly:

```bash
curl -X POST http://localhost:8000/ingestion/run \
  -H 'Content-Type: application/json' \
  -d '{"plugins":["alibaba_open_api"],"query":{"query":"ice roller","limit":25}}'
```

For now, `alibaba_mock` remains the default supplier plugin so the pipeline keeps working without live supplier credentials.

### Amazon Selling Partner API

The `amazon_sp_api` ingestion plugin is installed but disabled by default. Use the sandbox first with a sandbox refresh token, then switch to production after self-authorizing the production app.

Required local values for sandbox:

```bash
AMAZON_SP_API_ENABLED=true
AMAZON_SP_API_ENV=sandbox
AMAZON_SP_API_ENDPOINT=https://sandbox.sellingpartnerapi-na.amazon.com
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
AMAZON_LWA_CLIENT_ID=replace_me
AMAZON_LWA_CLIENT_SECRET=replace_me
AMAZON_LWA_REFRESH_TOKEN=replace_me
```

The sandbox endpoint defaults to `https://sandbox.sellingpartnerapi-na.amazon.com` for North America. Production defaults to `https://sellingpartnerapi-na.amazon.com` when `AMAZON_SP_API_ENV=production` and `AMAZON_SP_API_ENDPOINT` is not explicitly set. The backend also accepts the older names `AMAZON_SP_API_ENVIRONMENT` and `AMAZON_REFRESH_TOKEN` for compatibility.

Run the Catalog Items plugin explicitly:

```bash
curl -X POST http://localhost:8000/ingestion/run \
  -H 'Content-Type: application/json' \
  -d '{"plugins":["amazon_sp_api"],"query":{"query":"ice roller","limit":10}}'
```

Run the minimal connectivity test through the backend container:

```bash
docker compose exec -T \
  -e AMAZON_SP_API_CONNECTIVITY_TEST=1 \
  backend python -m pytest app/tests/test_amazon_sp_api_connectivity.py -q
```

The connectivity test exchanges the configured refresh token and performs a read-only
competitive-pricing lookup, which requires the Pricing role. It does not create,
update, or ingest product records.

The shared Amazon client already includes a Product Fees helper, so the next Amazon module can replace heuristic fee assumptions with SP-API fee estimates.

## SP-API Production Readiness

Compliance guardrails live in `compliance/`:

- `SECURITY.md`
- `ACCESS_CONTROL.md`
- `INCIDENT_RESPONSE.md`
- `NETWORK_SECURITY.md`
- `CREDENTIAL_MANAGEMENT.md`
- `AMAZON_DATA_HANDLING.md`
- `REVIEW_LOG.md`
- `AMAZON_DEVELOPER_PROFILE_RESPONSES.md`

Run the local compliance status check:

```bash
cd backend
python3 -m app.security.compliance_check
```

Or call the internal endpoint:

```bash
curl http://localhost:8000/security/compliance-status
```

The compliance status output reports booleans and missing environment variable names only. It must not expose secrets.

Production guardrails:

- `APP_ENV=production` fails fast unless `ALLOW_PUBLIC_UNAUTHENTICATED=true` is explicitly set.
- `PUBLIC_APP_URL` should be HTTPS for any non-local deployment.
- `COMPLIANCE_DOCS_PATH` points the backend to the compliance docs. Docker Compose mounts `./compliance` read-only at `/compliance`.
- This app is still a private internal tool. Do not expose it publicly without deployment-layer authentication or a real admin auth layer.

### Cost Ceiling Engine

The economics analyzer now calculates the max landed cost per product:

```text
max_landed_cost =
  selling_price
  - amazon_fees
  - inbound_cost_per_unit
  - storage_estimate
  - return_allowance
  - ad_allowance
  - target_profit
```

For now `amazon_fees` are estimated from configurable defaults. When Amazon SP-API is approved, a Product Fees ingestion/analyzer plugin can replace those assumptions with live fee estimates without changing the cost-ceiling formula.

Manual supplier quotes can flow through `manual_csv` using these optional columns:

```text
unit_cost, moq, lead_time_days, shipping_estimate, supplier_name, country
```

The product detail page shows max landed cost, supplier landed cost, Amazon fees, target profit, and margin of safety.

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
- Manual CSV, Amazon mock, Alibaba mock, Reddit mock, Google Trends mock, and opt-in Amazon SP-API/Etsy/Alibaba API ingestion plugins.
- Demand, competition, supplier, economics, risk, and review analyzer plugins.
- Compliance documents, secret redaction, production startup guardrails, and an internal compliance status endpoint.
- Content-hash observation deduplication.
- Simple alias-based product normalization.
- Versioned, explainable scoring engine.
- REST endpoints for products, opportunities, plugins, plugin runs, health, and pipeline trigger.
- Next.js terminal UI for dashboard, search, product detail, plugins, and run history.
