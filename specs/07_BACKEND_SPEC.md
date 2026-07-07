# Backend Spec

## Backend Goals

The backend should provide:

- plugin execution
- persistence
- normalization
- analysis
- scoring
- REST API
- local development support

## Backend Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pydantic v2
- pytest
- Ruff
- mypy

## Directory Structure

```text
backend/
  app/
    main.py
    api/
      routes/
        health.py
        products.py
        opportunities.py
        plugins.py
        ingestion.py
    core/
      config.py
      logging.py
    db/
      session.py
      base.py
    models/
      product.py
      observation.py
      signal.py
      insight.py
      score.py
      plugin_run.py
    schemas/
      product.py
      observation.py
      score.py
      plugin.py
    services/
      normalization_service.py
      scoring_service.py
      product_service.py
      plugin_service.py
    pipeline/
      runner.py
      ingestion_runner.py
      analyzer_runner.py
    plugins/
      ingestion/
      analyzers/
    scoring/
      formulas.py
      config.py
    tests/
  alembic/
  pyproject.toml
```

## API Endpoints

### Health

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

### Products

`GET /products`

Query params:

- `q`
- `category`
- `min_score`
- `recommendation`
- `limit`
- `offset`

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "canonical_name": "facial ice roller",
      "category": "beauty",
      "latest_score": 87,
      "recommendation": "strong_opportunity"
    }
  ],
  "total": 1
}
```

`GET /products/{id}`

Response should include:

- product
- aliases
- latest opportunity score
- market signals
- supplier signals
- cost models
- insights
- recent observations

### Opportunities

`GET /opportunities`

Returns ranked products by latest score.

Query params:

- `min_score`
- `category`
- `recommendation`
- `limit`
- `offset`

### Plugins

`GET /plugins`

Returns installed plugins.

```json
{
  "ingestion": [
    {
      "name": "manual_csv",
      "version": "0.1.0",
      "enabled": true
    }
  ],
  "analyzers": [
    {
      "name": "demand_analyzer",
      "version": "0.1.0",
      "enabled": true
    }
  ]
}
```

### Plugin Runs

`GET /plugin-runs`

Returns recent plugin runs.

### Run Ingestion

`POST /ingestion/run`

Body:

```json
{
  "plugins": ["manual_csv", "amazon_mock"],
  "query": {
    "category": "beauty",
    "limit": 100
  }
}
```

Response:

```json
{
  "status": "success",
  "plugin_runs": [
    {
      "plugin_name": "manual_csv",
      "status": "success",
      "records_created": 25
    }
  ],
  "products_updated": 12,
  "scores_updated": 12
}
```

## Services

### PluginService

Responsibilities:

- load plugin registry
- list installed plugins
- run selected plugins
- handle plugin errors

### NormalizationService

Responsibilities:

- transform raw observations into product candidates
- create aliases
- link observations to products
- deduplicate observations

### ProductService

Responsibilities:

- retrieve products
- retrieve product details
- search products

### ScoringService

Responsibilities:

- calculate component scores
- calculate final score
- generate explanation
- persist OpportunityScore

### PipelineRunner

Responsibilities:

- orchestrate full batch pipeline
- call plugin runners
- call normalization
- call analyzers
- call scoring
- return summary

## Database Migrations

Use Alembic.

Initial migration should create all MVP tables.

## Config

Use environment variables.

Required:

- `DATABASE_URL`
- `APP_ENV`
- `LOG_LEVEL`

Optional:

- `ENABLE_SCHEDULER`
- `DEFAULT_PIPELINE_LIMIT`

## Error Handling

- API errors should return structured JSON.
- Plugin errors should be captured in PluginRun.
- Pipeline should support partial success.
- Do not crash entire run due to one failed plugin unless all plugins fail.

## Testing Requirements

Backend tests must cover:

- plugin registry
- mock ingestion plugin output
- raw observation persistence
- normalization
- scoring formula
- API endpoints
- pipeline runner happy path
- plugin failure handling
