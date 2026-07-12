# Maintainability Guide

## Quality gate

Run `make check` before committing. It verifies migrations, backend tests, Python lint and types, frontend lint, and TypeScript. Run `make audit` when registry access is available.

## Data and scoring invariants

- Applied Alembic migrations are immutable. Add a forward migration for every schema change and keep `alembic check` clean.
- Product list rows are materialized from the latest `OpportunityScore.score_breakdown`. Any workflow that changes supplier quotes, constraints, comparables, or evidence must create a new score.
- Opportunity score, evidence confidence, validation readiness, and research priority are separate concepts. Do not multiply opportunity score by readiness.
- Comparable snapshots retain metric-level observation timestamps. A catalog refresh must not make carried-forward pricing or fees appear fresh.
- Validation marketplace packets and RFQs are immutable revisions. Create a new version instead of updating historical evidence or RFQ text in place.
- Validation quote economics use `Decimal` inputs and must expose input provenance. Missing price or fee evidence produces an incomplete calculation, never a hidden fallback.
- Validation project state is explicit and every manual transition is audited. Do not infer lifecycle state from quote or evidence presence.

## Validation workflow

- `ProductValidationService` owns lifecycle transitions, packet snapshots, RFQ revisions, quote economics, and decision gates. Keep business thresholds in typed settings, not route handlers.
- The legacy product-level supplier quote API remains for compatibility. New validation work must use project suppliers, quotes, and quantity tiers.
- Gate overrides require an actor and reason and are evidence, not score changes. POE evidence does not alter the global opportunity score.
- GET routes are read-only. Live Amazon refreshes occur only through the marketplace packet refresh action.

## Discovery execution

- `GET /discovery/runs` returns lightweight summaries by default. Fetch `/discovery/runs/{id}` for clusters, candidates, and origins.
- A worker must claim a queued run in the database before processing it. Backend startup requeues unfinished runs when `DISCOVERY_RECOVER_ON_STARTUP=true`.
- The current executor is intentionally a single in-process worker. It is suitable for this local, single-backend deployment but is not a distributed queue. Before running multiple backend replicas, move discovery jobs to a durable external worker system with leases and idempotent task delivery.

## Dependency maintenance

- Direct Python and frontend dependencies are pinned. Update them deliberately and include lockfile changes.
- Keep Next.js and PostCSS security advisories at zero with `make audit`.
- Recharts 2 is deprecated upstream. A future Recharts 3 migration should be handled as a dedicated UI change with chart regression testing.
