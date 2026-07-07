# Codex Implementation Instructions

## Role

You are implementing the MVP for the Product Discovery Terminal.

Treat the specs folder as the source of truth.

Build a working local-first application.

## Highest Priority

Implement the architecture correctly before adding features.

The MVP should prove:

```text
plugins ingest observations
→ observations normalize into products
→ analyzers generate insights
→ scoring ranks opportunities
→ UI displays explainable product recommendations
```

## Critical Rules

1. Do not build content generation.
2. Do not build social posting.
3. Do not build FBA listing creation.
4. Do not build order/inventory management.
5. Do not build real API integrations in the first pass.
6. Do not build event-driven AWS infrastructure.
7. Do not hardcode Amazon/FBA/TikTok/Alibaba into the core.
8. Use mock/manual plugins first.
9. Keep all source-specific logic inside plugins.
10. Make the pipeline runnable locally.

## Architecture Rule

The core should know about:

- observations
- products
- signals
- insights
- scores
- plugins

The core should not know about:

- Amazon implementation details
- TikTok implementation details
- Alibaba implementation details
- Etsy implementation details
- Reddit implementation details

## Implementation Approach

Build in this order:

1. Backend scaffold.
2. Database schema.
3. Plugin interfaces.
4. Mock ingestion plugins.
5. Ingestion pipeline.
6. Normalization.
7. Analyzer plugins.
8. Scoring engine.
9. REST API.
10. Frontend UI.
11. Tests.
12. Documentation.

## Local Development Requirement

The project must run with:

```bash
docker compose up
```

Prefer simple local services.

## MVP Plugins

Implement these first:

- manual_csv
- amazon_mock
- alibaba_mock
- reddit_mock
- google_trends_mock

These should produce enough sample data to demonstrate scoring.

## Scoring Requirement

Every scored product must have:

- component scores
- final score
- confidence score
- recommendation
- explanation

Do not only return a number.

## UI Requirement

The UI must allow the user to:

- run the pipeline
- view top opportunities
- search products
- inspect product details
- understand why a product was recommended
- see plugin run failures

## Testing Requirement

Add tests for:

- plugin loading
- ingestion
- normalization
- scoring
- API endpoints
- pipeline happy path
- plugin failure path

## Completion Criteria

Stop when the MVP works end-to-end with mock/manual data.

Do not continue into real external APIs unless explicitly instructed later.
