# Implementation Plan

## Guidance for Coding Agent

Implement this project in milestones.

Do not attempt every real API integration at once.

Use mock plugins first.

The goal is to prove the architecture and end-to-end product intelligence loop.

## Milestone 1: Repository Scaffold

Create:

```text
backend/
frontend/
specs/
docker-compose.yml
README.md
```

Backend:

- FastAPI app
- health endpoint
- pyproject
- pytest setup
- Ruff/mypy config

Frontend:

- Next.js app
- Tailwind
- basic layout

Docker:

- Postgres
- backend
- frontend

Acceptance:

- `docker compose up` starts all services.
- `GET /health` works.
- Frontend loads.

## Milestone 2: Database Schema

Implement SQLAlchemy models and Alembic migrations for:

- ProductCandidate
- ProductAlias
- RawObservation
- PluginRun
- MarketSignal
- SupplierSignal
- CostModel
- ProductInsight
- OpportunityScore

Acceptance:

- migrations run successfully
- tables created
- basic model tests pass

## Milestone 3: Plugin Framework

Implement:

- IngestionPlugin protocol
- AnalyzerPlugin protocol
- plugin registry
- plugin listing endpoint
- PluginRun tracking

Initial plugins:

- manual_csv
- amazon_mock
- alibaba_mock
- reddit_mock
- google_trends_mock

Acceptance:

- `GET /plugins` lists plugins
- plugin unit tests pass
- mock plugins return valid DTOs

## Milestone 4: Ingestion Pipeline

Implement:

- `POST /ingestion/run`
- ingestion runner
- raw observation persistence
- content hash deduplication
- plugin run status tracking

Acceptance:

- API call runs selected plugins
- raw observations are stored
- plugin run records are created
- duplicate observations are not repeatedly inserted

## Milestone 5: Normalization

Implement:

- product name cleaning
- simple alias matching
- ProductCandidate creation
- ProductAlias creation
- observation-product linking

Acceptance:

- similar observations map to the same product when obvious
- new products are created when no match exists
- tests cover alias matching

## Milestone 6: Analyzer Plugins

Implement analyzer plugins:

- demand analyzer
- competition analyzer
- supplier analyzer
- economics analyzer
- risk analyzer
- simple review/pain point analyzer

Acceptance:

- analyzers run after normalization
- analyzers create signals/insights/cost models
- analyzer failures are captured without crashing whole pipeline

## Milestone 7: Scoring Engine

Implement:

- configurable scoring weights
- component score calculation
- confidence score
- recommendation bands
- explanation generation
- score persistence

Acceptance:

- every updated product gets an OpportunityScore
- scores are visible through API
- tests verify scoring formula

## Milestone 8: Backend Product APIs

Implement:

- `GET /products`
- `GET /products/{id}`
- `GET /opportunities`
- `GET /plugin-runs`

Acceptance:

- dashboard can retrieve ranked products
- product detail returns evidence and insights
- filtering works for basic fields

## Milestone 9: Frontend Terminal UI

Implement pages:

- dashboard
- products
- product detail
- plugins
- runs

Acceptance:

- user can run pipeline from UI
- user can see ranked opportunities
- user can inspect product detail and score thesis
- user can inspect plugin failures

## Milestone 10: Polish and Documentation

Add:

- README
- local setup instructions
- seed data
- sample CSV
- tests
- screenshots if possible

Acceptance:

- new developer can run project locally
- tests pass
- README explains architecture and plugin extension

## Strict Build Order

Do not add real APIs before Milestone 10.

The first complete version should work entirely with mock/manual plugins.

## First Real API Candidates Later

After MVP:

1. Etsy or Reddit, if API access is easiest.
2. Google Trends through an approved/available route or manual import.
3. Amazon SP-API only when seller-account use case is needed.
4. Supplier data through manual CSV before Alibaba API/scraping.

## Definition of Done

The project is ready for real API expansion when:

- core pipeline works with mock data
- adding a plugin requires no core modifications
- scoring is explainable
- UI supports investigation workflow
- tests cover plugin/pipeline/scoring
