# Architecture

## Summary

The MVP should use a simple scheduled batch architecture.

```text
Scheduler
  ↓
Ingestion Plugins
  ↓
RawObservation Store
  ↓
Normalization
  ↓
ProductCandidate Store
  ↓
Analyzer Plugins
  ↓
Opportunity Scoring
  ↓
FastAPI
  ↓
Next.js Terminal UI
```

Do not build a distributed event-driven system for the MVP.

## Architecture Goals

- Low cost
- Local-first development
- Plugin-based ingestion
- Source-agnostic core
- Simple debugging
- Clear data lineage
- Easy to add new data sources
- Easy to replace mock plugins with real APIs later

## Recommended Stack

### Backend

- Python
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Pydantic
- APScheduler or simple cron-like scheduler
- pytest
- Ruff
- mypy

### Frontend

- Next.js
- TypeScript
- TailwindCSS
- shadcn/ui
- TanStack Query
- Recharts or lightweight charting library

### Local Development

- Docker Compose
- Backend container
- Frontend container
- PostgreSQL container

### Deployment Later

For MVP deployment, prefer low-cost options:

- single VPS
- Railway
- Render
- Fly.io
- Supabase Postgres
- Neon Postgres

Avoid AWS-heavy architecture initially.

## Core Components

### 1. Scheduler

Responsible for triggering pipeline runs.

MVP behavior:

- manually trigger from API/UI
- optionally run on a simple interval
- no distributed queue required

### 2. Ingestion Plugin Runner

Loads enabled ingestion plugins and calls their `fetch()` method.

Each plugin returns `RawObservation` objects.

### 3. Raw Observation Store

Stores all incoming evidence without destructive transformation.

This provides auditability and reprocessing ability.

### 4. Normalization Layer

Maps raw observations to canonical `ProductCandidate` records.

Responsibilities:

- clean product names
- infer categories
- detect aliases
- link observations to products
- avoid duplicate products where possible

### 5. Product Graph Layer

MVP can be relational Postgres tables.

Do not use Neo4j or a separate graph database initially.

Represent the graph through relational relationships:

- ProductCandidate
- ProductAlias
- RawObservation
- MarketSignal
- SupplierSignal
- ProductInsight
- CostModel
- OpportunityScore

### 6. Analyzer Plugin Runner

Runs analysis plugins on products.

Analyzer plugins create derived insights such as:

- demand score inputs
- review complaint clusters
- competition metrics
- supplier economics
- risk flags

### 7. Opportunity Engine

Combines normalized signals and insights into explainable opportunity scores.

### 8. REST API

Serves products, scores, plugin runs, and details to the UI.

### 9. Terminal UI

Interactive dashboard for browsing, filtering, and comparing product opportunities.

## Data Flow

```text
POST /ingestion/run
  ↓
Create PluginRun
  ↓
Run selected ingestion plugins
  ↓
Persist RawObservations
  ↓
Normalize observations
  ↓
Create/update ProductCandidates
  ↓
Run analyzers
  ↓
Compute OpportunityScores
  ↓
Return run summary
```

## Event-Compatible, Not Event-Driven

The design should preserve clear stage boundaries:

```text
observation_created
product_normalized
analysis_completed
score_updated
```

But these are conceptual events, not infrastructure requirements.

For the MVP, implement them as function calls inside a batch job.

Later, if needed, these stages can map to queue messages.

## Source-Agnostic Core Rule

No source-specific logic should exist in core services.

Bad:

```python
if source == "amazon":
    calculate_amazon_score()
```

Good:

```python
for analyzer in analyzer_registry.enabled():
    analyzer.analyze(product_context)
```

Source-specific behavior belongs inside plugins or analyzers.

## Recommended Repository Structure

```text
product-discovery-terminal/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      plugins/
        ingestion/
        analyzers/
      scoring/
      pipeline/
      tests/
    alembic/
    pyproject.toml
  frontend/
    app/
    components/
    lib/
    types/
    package.json
  specs/
  docker-compose.yml
  README.md
```

## Cost Controls

- Run locally first.
- No Kafka.
- No SQS.
- No Lambda fan-out.
- No managed OpenSearch.
- No large background worker fleets.
- No always-on GPU.
- Use mock data before paid APIs.
- Cache API responses.
- Track plugin run costs if paid APIs are added.
