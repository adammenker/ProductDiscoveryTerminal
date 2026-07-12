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

Run the complete local quality gate before committing:

```bash
make check
```

Dependency audits are separate because they require registry access:

```bash
make audit
```

Repository invariants and known operational limits are documented in [docs/MAINTAINABILITY.md](docs/MAINTAINABILITY.md).

Services:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Health: <http://localhost:8000/health>
- Postgres: `localhost:5432`

Open the frontend, type a product keyword in the dashboard search bar, and fetch real Amazon evidence through the SP-API research flow. Use `/discovery` for seed-list based scanner runs that can turn broad keywords into multiple candidate concepts, preliminarily rank them, enrich the top candidates with pricing/fees, and finalize rankings. Mock/sample plugins are still available for explicit development runs, but the default product research UI does not seed demo data.

## Product Validation

Use `/validations` to turn a ranked opportunity into a structured research project:

```text
ranked opportunity -> immutable marketplace packet -> manual POE evidence
-> versioned RFQ -> supplier quotes and quantity tiers -> landed-cost comparison
-> explicit decision gates -> reject or approve for sample
```

Start a validation from a discovery result or product detail page. The project freezes the exact recommendation snapshot and creates a versioned marketplace packet; later product rescoring does not rewrite that basis. Marketplace refreshes create new packet versions, RFQ edits create revisions, and every status transition is audited. Supplier research, freight, duty, inspection, and other sourcing estimates remain manual and must be verified before ordering.

Validation does not approve purchases or guarantee product success. `Approve for sample` records a research decision only.

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

`alibaba_mock` remains available for explicit development/testing runs, but it is
never selected automatically.

Mock and bundled sample plugins are explicit-run only. A pipeline request without
plugin names does not ingest demo data. The live dashboard therefore contains only
production API observations or user-provided manual imports and supplier quotes.

### Amazon Selling Partner API

Amazon research is split into three opt-in plugins:

- `amazon_catalog_spapi` searches Catalog Items and preserves Amazon category/product-type context.
- `amazon_pricing_spapi` fetches competitive pricing and offer-count evidence for relevant ASINs.
- `amazon_fees_spapi` fetches Product Fees estimates only for final effective comparables.

The old combined `amazon_sp_api` plugin has been removed from the default registry to prevent duplicate ingestion. The backend research pipeline orchestrates the child plugins in a two-pass flow:

```text
catalog search
-> preliminary comparable relevance
-> pricing for included/needs-review ASINs
-> final comparable relevance
-> fees for final included ASINs
-> one marketplace snapshot cohort
-> Recommendation V2 scoring
```

Use the sandbox first with a sandbox refresh token, then switch to production after self-authorizing the production app.

Required local values for sandbox:

```bash
AMAZON_SP_API_ENABLED=true
AMAZON_SP_API_ENV=sandbox
AMAZON_SP_API_ENDPOINT=https://sandbox.sellingpartnerapi-na.amazon.com
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
AMAZON_LWA_CLIENT_ID=replace_me
AMAZON_LWA_CLIENT_SECRET=replace_me
AMAZON_LWA_REFRESH_TOKEN=replace_me
STORE_RAW_AMAZON_PAYLOADS=false
RAW_PAYLOAD_RETENTION_DAYS=7
DISCOVERY_ENRICH_TOP_N=20
DISCOVERY_MIN_CLUSTER_CONFIDENCE=0.60
DISCOVERY_ENRICHMENT_REQUEST_INTERVAL_SECONDS=2.0
DISCOVERY_ENRICH_MAX_PER_SOURCE_QUERY=3
DISCOVERY_ENRICH_MAX_PER_OPPORTUNITY=1
VALIDATION_MIN_EFFECTIVE_COMPARABLES=3
VALIDATION_MIN_CONFIDENCE=60
VALIDATION_MIN_SUPPLIER_QUOTES=3
VALIDATION_TARGET_MARGIN_PERCENT=30
VALIDATION_ADVERTISING_RESERVE_PERCENT=15
VALIDATION_RETURNS_RESERVE_PERCENT=5
VALIDATION_OTHER_VARIABLE_COST_PER_UNIT=0
VALIDATION_MARKETPLACE_MAX_AGE_DAYS=7
```

The sandbox endpoint defaults to `https://sandbox.sellingpartnerapi-na.amazon.com` for North America. Production defaults to `https://sellingpartnerapi-na.amazon.com` when `AMAZON_SP_API_ENV=production` and `AMAZON_SP_API_ENDPOINT` is not explicitly set. The backend also accepts the older names `AMAZON_SP_API_ENVIRONMENT` and `AMAZON_REFRESH_TOKEN` for compatibility.

SP-API calls use process-wide endpoint pacing for catalog, pricing, and fees. Throttled and transient server responses honor `Retry-After` and fall back to exponential backoff; temporary transport failures are retried as well.

Run a product research refresh through the API:

```bash
curl -X POST http://localhost:8000/ingestion/research \
  -H 'Content-Type: application/json' \
  -d '{"query":"camping cookware pot","limit":10}'
```

You can still run child plugins explicitly for diagnostics, but normal product discovery should use the research endpoint/UI search so comparable filtering happens before pricing and fees.

Run the minimal connectivity test through the backend container:

```bash
docker compose exec -T \
  -e AMAZON_SP_API_CONNECTIVITY_TEST=1 \
  backend python -m pytest app/tests/test_amazon_sp_api_connectivity.py -q
```

The connectivity test exchanges the configured refresh token and performs a read-only competitive-pricing lookup, which requires the Pricing role. It does not create, update, or ingest product records.

### Validation-first workflow

Discovery candidates now flow through:

```text
candidate -> comparable ASINs -> economics -> supplier quotes
          -> constraints -> evidence matrix -> decision -> paper trade
```

The product detail API exposes `economics_validator`, `supplier_validation`,
`constraint_evaluation`, `evidence_matrix`, `validation_decision`, and
`paper_trading_history`. Cost ceilings include 20%, 30%, 40%, and 50% target
margin scenarios plus a low/modeled/high sensitivity table.

Useful manual endpoints:

```text
POST /products
POST /products/{id}/supplier-quotes
POST /supplier-quotes/import-text
POST /products/{id}/evaluate-constraints
POST /products/{id}/snapshots
POST /paper-trades/{id}/outcomes
GET  /backtests/summary
POST /discovery/seed-lists
GET  /discovery/seed-lists
POST /discovery/runs
GET  /discovery/runs
GET  /discovery/runs/{id}
```

Product Opportunity Explorer remains manual-only. Run
`product_opportunity_explorer_manual_csv` with `query.metadata.file_path` to
import a user-provided CSV; the application does not scrape Seller Central.

Amazon fee estimates based on comparable ASINs are always proxies, not guaranteed actual fees. Each fee estimate carries provenance (`live_spapi`, `comparable_proxy`, `configured_fallback`, or `missing`) so configured fallbacks cannot look equivalent to live ASIN-based fee estimates.

Recommendation V2 is the source of truth for product decisions. The legacy score fields remain for API compatibility; a legacy numeric zero may represent a V2 null or insufficient-data state.

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

`amazon_fees` come from Product Fees estimates when an effective comparable has usable pricing. Configured defaults are retained only as low-confidence fallback evidence and do not satisfy the same validation checks as live fee estimates.

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
python3 -m mypy app
python3 -m app.evaluation --out evaluation_reports --k 10
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

Additional design notes:

- [Recommendation Engine V2](docs/RECOMMENDATION_ENGINE_V2.md)
- [Amazon Research Pipeline](docs/AMAZON_RESEARCH_PIPELINE.md)
- [Comparable Relevance](docs/COMPARABLE_RELEVANCE.md)
- [Historical Signals](docs/HISTORICAL_SIGNALS.md)
- [Discovery Runs](docs/DISCOVERY_RUNS.md)
- [Evaluation Harness](docs/EVALUATION_HARNESS.md)

## Implemented MVP

- FastAPI backend with SQLAlchemy models and Alembic migration.
- Postgres through Docker Compose, SQLite-compatible local tests.
- Manual CSV, Amazon mock, Alibaba mock, Reddit mock, Google Trends mock, and opt-in Amazon Catalog/Pricing/Fees SP-API, Etsy, and Alibaba API ingestion plugins.
- Demand, competition, supplier, economics, risk, and review analyzer plugins.
- Compliance documents, secret redaction, production startup guardrails, and an internal compliance status endpoint.
- Content-hash observation deduplication.
- Simple alias-based product normalization.
- Versioned, explainable Recommendation V2 engine with separate opportunity, confidence, and readiness scores.
- Comparable-ASIN relevance filtering, manual comparable overrides, and idempotent marketplace snapshot cohorts.
- Seed-list discovery runs that cluster broad searches into multiple product candidates.
- Offline Recommendation V2 evaluation harness with JSON/Markdown reports.
- REST endpoints for products, opportunities, plugins, plugin runs, health, and pipeline trigger.
- Next.js terminal UI for dashboard, search, product detail, plugins, and run history.
