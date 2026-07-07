# Testing and Quality

## Testing Philosophy

The most important risk is architectural drift.

Tests should ensure:

- plugins remain isolated
- source-specific logic stays out of the core
- pipeline stages work independently
- scoring is deterministic
- failures are visible

## Backend Test Categories

### Unit Tests

Test:

- DTO validation
- plugin output validation
- content hashing
- product name cleaning
- alias matching
- scoring formulas
- recommendation bands
- risk scoring

### Plugin Tests

Each plugin must have tests proving:

- it returns valid DTOs
- it handles empty results
- it handles malformed source data
- it does not write to DB directly

### Pipeline Tests

Test:

- ingestion happy path
- plugin failure path
- partial success
- duplicate observation handling
- normalization flow
- analyzer flow
- scoring flow

### API Tests

Test:

- health endpoint
- products list
- product detail
- opportunities
- plugin list
- plugin runs
- ingestion trigger

## Frontend Tests

MVP frontend testing can be lighter.

Test or manually verify:

- dashboard renders empty state
- dashboard renders opportunities
- product table filters
- product detail loads
- plugin run failures display
- run pipeline button handles loading/error/success

## Static Quality

Use:

- Ruff
- mypy
- TypeScript strict mode
- ESLint
- Prettier

## Observability

MVP logging should include:

- pipeline start/end
- plugin start/end
- records fetched
- records inserted
- normalization counts
- analyzer counts
- scoring counts
- errors

No complex observability platform is required.

## Data Quality Checks

Add simple checks:

- observations must have source
- observations must have entity_type
- observations should have title or raw_text
- scores must be 0-100
- final score must be 0-100
- recommendations must match enum

## Architecture Guardrails

Codex/coding agent should maintain these guardrails:

1. No real API work until mock pipeline works.
2. No source-specific logic in core services.
3. No event-driven cloud infrastructure in MVP.
4. No content generation.
5. No FBA execution workflows.
6. No inventory/order management.
7. Keep plugin interfaces stable.
8. Keep scoring explainable.

## Manual QA Script

After implementation, run:

1. Start Docker Compose.
2. Open frontend.
3. Verify no products initially.
4. Click Run Pipeline.
5. Verify plugin runs complete.
6. Verify products appear.
7. Verify opportunities are ranked.
8. Open product detail.
9. Verify score breakdown appears.
10. Verify evidence/observations are visible.
11. Run pipeline again.
12. Verify duplicates are not created excessively.
13. Disable/break one mock plugin.
14. Verify partial failure is visible and other plugins still run.

## Performance Expectations

MVP should handle:

- 1,000 raw observations
- 100 product candidates
- 10 mock plugins
- full pipeline run under a few minutes locally

Do not optimize prematurely.
