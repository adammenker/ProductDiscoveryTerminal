# Codex Implementation Plan — Gap Specs

## Goal

Implement the next phase without breaking the existing MVP.

The current repo already has the foundation. This plan adds validation-first product discovery.

## Build Order

### Milestone 1: Amazon SP-API Config and Client

Implement:

- env vars
- sandbox/production switch
- token exchange/cache
- secret redaction
- disabled plugin state
- mocked tests

Do not yet integrate into scoring.

Acceptance:

- tests pass without real credentials
- missing credentials disable plugins cleanly
- no credentials exposed in API/frontend

### Milestone 2: Amazon Comparable ASIN Plugins

Implement:

- `amazon_catalog_spapi`
- `amazon_pricing_spapi`
- `amazon_fees_spapi`
- fixture-based tests

Acceptance:

- catalog maps to RawObservation
- pricing maps to MarketSignal
- fees map to CostModel
- product detail can show comparable ASINs
- Amazon catalog search can act as a discovery source

### Milestone 3: Cost Ceiling Engine V2

Implement:

- multiple target margin scenarios
- sensitivity table
- source priority
- fee-source metadata
- decisions for invalid/missing data

Acceptance:

- cost ceiling uses Amazon fee CostModel when present
- defaults still work without Amazon plugin
- product detail API exposes economics validator

### Milestone 4: Supplier Validation

Implement:

- SupplierQuote model or equivalent SupplierSignal metadata
- manual quote CRUD
- CSV import enhancements
- landed cost calculation
- quote vs ceiling validation

Acceptance:

- user can add supplier quote
- product detail shows quote status
- scoring reacts to below/above ceiling

### Milestone 5: Constraints and Rule Profile

Implement:

- default conservative FBA rule profile
- structured risk flags
- constraint evaluation
- scoring blocks strong_opportunity on hard failures

Acceptance:

- no-battery/no-liquid/no-supplement rules work
- product filters can hide ineligible products

### Milestone 6: Cross-Source Evidence Matrix

Implement:

- evidence matrix service
- cross-source confidence score
- upgraded opportunity thesis
- manual Product Opportunity Explorer CSV import

Acceptance:

- product detail shows source agreement/missing evidence
- strong_opportunity requires supplier validation + constraints + economics
- discovery source is included in evidence

### Milestone 7: Backtesting / Paper Trading

Implement:

- OpportunitySnapshot
- PaperTrade
- OutcomeMeasurement
- manual outcome entry
- aggregate simple metrics

Acceptance:

- user can snapshot top opportunities
- old snapshots are immutable
- backtest page shows outcome rates
- backtest can group by discovery source

### Milestone 8: Frontend Validation-First Discovery UI

Implement:

- `/validator`
- product detail sections
- dashboard category buckets
- paper trade controls

Acceptance:

- user can discover or enter a product and validate it end-to-end
- UI clearly explains assumptions and missing data
- discovery remains visible as the first stage

## Required Tests

Add tests for each milestone.

Before final handoff, run:

```bash
cd backend
python3 -m pytest
python3 -m ruff check app

cd ../frontend
pnpm typecheck
pnpm build
```

## Guardrails

Do not:

- scrape Seller Central
- scrape Product Opportunity Explorer
- hardcode Amazon into core scoring logic
- remove mock plugins
- remove local-first behavior
- require paid APIs for tests
- build content generation
- build FBA listing/order/inventory automation
- turn the app into a calculator-only tool with no discovery workflow

## Final Acceptance Criteria

The next phase is done when:

- SP-API production plugins are optional and working behind env config.
- Products can be discovered from plugins/manual input and validated from keyword to decision.
- Cost ceilings use live Amazon fee estimates when available.
- Supplier quotes determine whether economics are viable.
- Custom constraints block bad products.
- Cross-source evidence matrix explains why a product is or is not compelling.
- Paper-trading snapshots allow future validation.
- Existing MVP tests still pass.
