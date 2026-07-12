# 22 — Product Validation Pipeline

## Objective

Turn a ranked product recommendation into a structured validation project that gathers increasingly concrete evidence before the user commits to samples or inventory.

The primary user flow must become:

```text
Seed list
→ Discovery run
→ Ranked opportunity
→ Start validation
→ Marketplace evidence packet
→ RFQ generation
→ Supplier quote entry
→ Landed-cost comparison
→ Decision gates
→ Reject or Approve for sample
```

The system must not require the user to already know whether a product is “good.” It should guide the user through evidence collection and make the remaining uncertainties explicit.

---

## Important implementation rule

Before adding new tables or services, inspect the existing validation domain, especially:

```text
backend/app/services/validation_service.py
backend/app/models/
backend/app/schemas/
backend/app/api/routes/
frontend/app/validator/
```

Reuse and extend existing validation concepts where possible.

Do **not** create a second parallel validation system if the repository already has equivalent entities or statuses. Migrate or rename existing concepts only when necessary.

---

## Non-goals

This milestone must **not** include:

- Alibaba, Global Sources, Made-in-China, or other supplier APIs
- automated supplier discovery
- automated supplier outreach
- purchase orders or payments
- freight booking
- customs-broker integrations
- AI-generated final approval decisions
- automatic inventory purchases
- automatic scoring-weight changes
- review scraping
- Customer Feedback API integration
- ML-based recommendation or supplier ranking

Supplier research remains manual. The application should generate a structured RFQ, store supplier quotes, calculate economics, and enforce transparent decision gates.

---

# Milestone order

Implement in this order:

1. Validation project lifecycle
2. Immutable marketplace evidence packet
3. Manual Product Opportunity Explorer evidence
4. RFQ generation
5. Supplier and quote tracking
6. Landed-cost and margin calculations
7. Decision gates and status transitions
8. API and frontend workflow
9. Tests, migrations, documentation, and completion report

Each milestone must pass tests before starting the next.

---

# 1. Validation project lifecycle

## Required behavior

A user must be able to start validation from:

- a discovery-run result
- a product detail page
- an existing recommendation snapshot

Starting validation must capture the exact recommendation that triggered the project.

A later product rescore must not silently rewrite the original validation basis.

## Suggested entity

Reuse an existing validation entity if one exists. Otherwise add:

```python
class ProductValidationProject:
    id: UUID
    product_id: UUID
    source_discovery_run_id: UUID | None
    source_discovery_result_id: UUID | None
    source_recommendation_snapshot_id: UUID

    status: ValidationStatus
    title: str
    notes: str | None

    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
```

## Statuses

Use an explicit enum:

```text
draft
marketplace_validation
sourcing
ready_for_decision
approved_for_sample
rejected
archived
```

Do not infer project state from the presence of quotes or JSON fields.

## Transition rules

```text
draft
→ marketplace_validation

marketplace_validation
→ sourcing
→ rejected

sourcing
→ ready_for_decision
→ rejected

ready_for_decision
→ approved_for_sample
→ sourcing
→ rejected

approved_for_sample
→ archived

rejected
→ marketplace_validation
→ archived
```

Invalid transitions must return a clear API error.

Every manual transition must record:

```text
from_status
to_status
reason
actor
timestamp
```

For now, `actor` may be a simple string such as `"local_user"`.

## Duplicate prevention

Only one active validation project should exist for the same product and source recommendation snapshot.

Creating a duplicate must return the existing project rather than creating another one.

---

# 2. Immutable marketplace evidence packet

## Purpose

The marketplace packet records the evidence available when validation begins or when the user explicitly refreshes it.

It must answer:

```text
Why did this product rank highly?
What evidence supports demand?
What evidence supports competition?
What economics are currently estimated?
Which comparable ASINs were used?
What is missing, stale, or conflicting?
What is the maximum viable landed cost?
```

## Snapshot behavior

Create a new immutable packet version when:

- validation begins
- the user clicks `Refresh marketplace evidence`
- effective comparables change
- a new recommendation snapshot is explicitly adopted

Do not update an existing packet in place.

## Suggested entity

```python
class ValidationMarketplacePacket:
    id: UUID
    validation_project_id: UUID
    version: int

    recommendation_snapshot_id: UUID
    scoring_version: str

    opportunity_score: float | None
    confidence_score: float | None
    readiness_score: float | None
    research_priority_score: float | None

    expected_sale_price: Decimal | None
    amazon_fees_per_unit: Decimal | None
    max_landed_cost: Decimal | None

    effective_comparable_count: int
    comparable_asins: list[str]

    demand_summary: dict
    competition_summary: dict
    economics_summary: dict
    risk_summary: dict
    missing_evidence: list[str]
    conflicting_evidence: list[str]

    observed_at: datetime
    created_at: datetime
```

JSON fields must preserve source provenance and observation timestamps where available.

## Comparable detail

The packet should include a stable comparable summary for every effective comparable:

```json
{
  "asin": "B0...",
  "title": "...",
  "brand": "...",
  "price": 24.99,
  "price_observed_at": "...",
  "sales_rank": 18420,
  "rank_category": "...",
  "rank_observed_at": "...",
  "review_count": 821,
  "rating": 4.3,
  "fee_estimate": 8.12,
  "fee_provenance": "live_spapi",
  "relevance_status": "included",
  "relevance_score": 0.91
}
```

All packet calculations must use the repository’s canonical effective-comparable accessor. Do not reimplement inclusion logic.

## Refresh behavior

Refreshing a validation packet may call the existing Amazon refresh pipeline, but it must:

1. refresh Amazon evidence;
2. create a new recommendation snapshot;
3. create a new validation packet version;
4. preserve all older versions;
5. never rewrite supplier quotes.

---

# 3. Manual Product Opportunity Explorer evidence

## Purpose

Allow the user to add stronger Amazon-native demand evidence without requiring an API integration.

## Suggested entity

```python
class ValidationPoeEvidence:
    id: UUID
    validation_project_id: UUID

    niche_name: str | None
    reporting_period: str | None

    search_volume: int | None
    search_volume_growth_percent: Decimal | None
    product_count: int | None
    average_price: Decimal | None
    average_review_count: Decimal | None
    conversion_rate: Decimal | None
    click_share_top_products_percent: Decimal | None
    unmet_demand_notes: str | None

    source_url: str | None
    observed_at: datetime | None
    entered_at: datetime
    notes: str | None
```

Fields should be optional because POE screens and exports may vary.

## Validation rules

- percentages must be within sensible ranges;
- values must never be silently converted between fractions and percentages;
- `observed_at` must be shown in the UI;
- manually entered evidence must be labeled `manual_poe`.

## Scoring rule

Do not automatically alter the global opportunity score in this milestone.

POE evidence should affect validation gates and packet confidence only through explicit, documented validation rules.

---

# 4. RFQ generation

## User action

The validation detail page must include:

```text
Generate RFQ
```

The RFQ should be editable after generation.

## RFQ contents

Generate a structured request containing:

```text
Product working name
Product concept description
Reference comparable ASINs
Reference product URLs, if available
Target customer/use case
Required dimensions
Required materials
Required colors/variants
Required customization
Packaging requirements
Labeling/barcode requirements
Target quantities: 200, 500, 1,000
Destination country/postal code
Required certifications
Requested sample cost
Requested MOQ
Requested production lead time
Requested EXW price
Requested FOB price
Tooling/mold fees
Payment terms
Quality-control process
Factory audit/certification evidence
```

Unknown fields must appear as clearly marked placeholders rather than fabricated values.

## Suggested entity

```python
class ValidationRfq:
    id: UUID
    validation_project_id: UUID
    version: int

    title: str
    product_specification: dict
    requested_quantities: list[int]
    destination: dict
    required_certifications: list[str]
    questions: list[str]

    rendered_markdown: str
    created_at: datetime
    updated_at: datetime
```

## Export

Support:

- copy-to-clipboard from the frontend;
- Markdown download;
- plain-text download.

PDF generation is not required.

## RFQ versioning

Editing an RFQ should create a new version or maintain an explicit revision history.

A supplier quote must indicate which RFQ version it answered.

---

# 5. Supplier and quote tracking

## Supplier entity

```python
class Supplier:
    id: UUID
    name: str
    platform: SupplierPlatform
    profile_url: str | None
    location: str | None
    contact_name: str | None
    contact_details: dict | None
    verified_status: str | None
    years_in_business: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

Suggested platforms:

```text
alibaba
global_sources
made_in_china
importyeti
direct
sourcing_agent
other
```

Do not treat a platform badge as proof that the factory is trustworthy.

## Quote entity

A quote must support quantity-specific pricing.

```python
class SupplierQuote:
    id: UUID
    validation_project_id: UUID
    supplier_id: UUID
    rfq_id: UUID | None

    currency: str
    incoterm: str | None

    moq: int | None
    sample_cost: Decimal | None
    tooling_cost: Decimal | None
    packaging_cost_per_unit: Decimal | None
    labeling_cost_per_unit: Decimal | None

    production_lead_time_days: int | None
    sample_lead_time_days: int | None

    certification_notes: str | None
    payment_terms: str | None
    quote_valid_until: date | None
    notes: str | None

    created_at: datetime
    updated_at: datetime
```

## Quantity tiers

Use a child table or structured rows:

```python
class SupplierQuoteTier:
    id: UUID
    supplier_quote_id: UUID

    quantity: int
    unit_price: Decimal

    freight_total: Decimal | None
    duty_total: Decimal | None
    inspection_total: Decimal | None
    prep_total: Decimal | None
    miscellaneous_total: Decimal | None
```

The UI must support at least:

```text
200 units
500 units
1,000 units
```

but allow arbitrary quantities.

## Quote states

```text
draft
received
clarification_needed
shortlisted
rejected
expired
```

## Manual data warning

Freight, duty, tariff, and inspection costs are manual estimates in this milestone.

The UI must display:

```text
Manual estimate — verify before ordering
```

---

# 6. Landed-cost and margin calculations

## Required calculations

For each quote tier calculate:

```text
unit_product_cost
unit_packaging_cost
unit_labeling_cost
unit_tooling_amortization
unit_freight_cost
unit_duty_cost
unit_inspection_cost
unit_prep_cost
unit_miscellaneous_cost
landed_cost_per_unit
```

Formula:

```text
landed_cost_per_unit =
    unit_product_cost
  + unit_packaging_cost
  + unit_labeling_cost
  + tooling_cost / quantity
  + freight_total / quantity
  + duty_total / quantity
  + inspection_total / quantity
  + prep_total / quantity
  + miscellaneous_total / quantity
```

## Profitability calculations

Use the marketplace packet’s expected selling price and Amazon fee estimates.

Configuration must include:

```text
target_contribution_margin_percent
advertising_reserve_percent
returns_reserve_percent
other_variable_cost_per_unit
```

Suggested formula:

```text
estimated_contribution_per_unit =
    expected_sale_price
  - amazon_fees_per_unit
  - landed_cost_per_unit
  - advertising_reserve
  - returns_reserve
  - other_variable_cost_per_unit
```

```text
estimated_contribution_margin_percent =
    estimated_contribution_per_unit / expected_sale_price
```

```text
max_landed_cost =
    expected_sale_price
  - amazon_fees_per_unit
  - target_contribution_amount
  - advertising_reserve
  - returns_reserve
  - other_variable_cost_per_unit
```

## Provenance

Every derived number must expose its source inputs.

Example:

```json
{
  "max_landed_cost": 7.42,
  "inputs": {
    "expected_sale_price": {
      "value": 24.99,
      "source": "validation_marketplace_packet_v3"
    },
    "amazon_fees": {
      "value": 8.11,
      "source": "live_spapi"
    },
    "advertising_reserve_percent": {
      "value": 0.15,
      "source": "validation_config"
    }
  }
}
```

## Missing values

Do not substitute hidden defaults.

If required inputs are absent:

```text
calculation_status = incomplete
missing_inputs = [...]
```

The UI must not display a precise profit estimate from incomplete data.

---

# 7. Decision gates and status transitions

## Purpose

The application should determine whether enough evidence exists to make the next decision.

It must not claim that a product is guaranteed to succeed.

## Gate structure

Every gate result must include:

```text
status: passed | failed | incomplete | overridden
summary
evidence
missing_inputs
evaluated_at
rule_version
```

## Marketplace evidence gate

Suggested initial requirements:

```text
effective comparable count >= configurable minimum
recommendation snapshot exists
price evidence is present
fee evidence is present
no unresolved comparable-review blockers
confidence >= configurable minimum
```

Do not hardcode thresholds inside route handlers.

## Sourcing evidence gate

Suggested initial requirements:

```text
at least 3 received supplier quotes
or explicit user override with reason

at least 1 quote includes:
- MOQ
- unit price
- lead time
- sample cost
```

The three-quote requirement must be configurable.

## Economics gate

Pass when at least one quote tier satisfies:

```text
landed_cost_per_unit <= max_landed_cost
estimated_contribution_margin_percent >= configured threshold
```

If expected price or Amazon fees are stale, return `incomplete` or require a marketplace refresh.

## Risk gate

Reuse the existing risk/constraint evaluation system.

Pass only when:

```text
risk evaluation status = completed
no blocking risk is unresolved
```

An empty `risk_flags` list alone must not prove that evaluation occurred.

## Decision readiness gate

Pass only when:

```text
marketplace gate = passed or overridden
sourcing gate = passed or overridden
economics gate = passed or overridden
risk gate = passed or overridden
```

## Overrides

Users may override a failed or incomplete gate only by providing:

```text
reason
timestamp
actor
```

The UI must show overrides prominently.

## Final decisions

Buttons:

```text
Approve for sample
Reject
Return to sourcing
Refresh marketplace evidence
```

Approving for sample must not create a purchase order.

---

# 8. API design

Adapt route names to the repository’s existing conventions.

## Validation projects

```http
POST /validation-projects
GET /validation-projects
GET /validation-projects/{project_id}
PATCH /validation-projects/{project_id}
POST /validation-projects/{project_id}/transition
```

Create request:

```json
{
  "product_id": "...",
  "recommendation_snapshot_id": "...",
  "source_discovery_run_id": "...",
  "source_discovery_result_id": "..."
}
```

## Marketplace packet

```http
GET /validation-projects/{project_id}/marketplace-packets
GET /validation-projects/{project_id}/marketplace-packets/latest
POST /validation-projects/{project_id}/marketplace-packets/refresh
```

## POE evidence

```http
GET /validation-projects/{project_id}/poe-evidence
PUT /validation-projects/{project_id}/poe-evidence
```

## RFQs

```http
POST /validation-projects/{project_id}/rfqs/generate
GET /validation-projects/{project_id}/rfqs
GET /validation-projects/{project_id}/rfqs/{rfq_id}
PATCH /validation-projects/{project_id}/rfqs/{rfq_id}
```

## Suppliers and quotes

```http
POST /suppliers
GET /suppliers
GET /suppliers/{supplier_id}
PATCH /suppliers/{supplier_id}

POST /validation-projects/{project_id}/quotes
GET /validation-projects/{project_id}/quotes
GET /validation-projects/{project_id}/quotes/{quote_id}
PATCH /validation-projects/{project_id}/quotes/{quote_id}
DELETE /validation-projects/{project_id}/quotes/{quote_id}
```

## Gates

```http
POST /validation-projects/{project_id}/gates/evaluate
GET /validation-projects/{project_id}/gates/latest
POST /validation-projects/{project_id}/gates/{gate_name}/override
```

## API requirements

- use repository-standard pagination;
- return typed schemas rather than unstructured dictionaries;
- preserve Decimal values safely;
- use idempotency where repeated button clicks could duplicate work;
- return clear validation errors;
- do not trigger live Amazon refreshes from GET requests.

---

# 9. Frontend workflow

## Primary pages

### Validation queue

Route:

```text
/validations
```

Show:

```text
product
status
latest opportunity score
confidence
max landed cost
quote count
best landed cost
decision readiness
updated time
```

Filters:

```text
status
decision readiness
category
has viable quote
missing marketplace evidence
```

### Validation detail

Route:

```text
/validations/{id}
```

Sections:

1. Overview
2. Marketplace evidence
3. POE evidence
4. RFQ
5. Suppliers and quotes
6. Economics
7. Risks
8. Decision gates
9. Audit history

## Entry points

Add `Start validation` to:

- discovery result cards;
- grouped opportunity cards;
- product detail page;
- recommendation detail.

If an active project already exists, display:

```text
Open validation
```

instead of creating a duplicate.

## Marketplace section

Show:

```text
recommendation snapshot version
scoring version
packet age
opportunity
confidence
readiness
expected sale price
Amazon fees
maximum landed cost
effective comparables
missing/conflicting evidence
```

## RFQ section

Support:

```text
Generate
Edit
Copy
Download Markdown
Download Text
View revision history
```

## Quote comparison table

Columns:

```text
supplier
quantity
unit price
landed cost
MOQ
sample cost
lead time
margin
meets cost ceiling
status
```

Allow sorting by:

```text
landed cost
margin
MOQ
lead time
```

The lowest unit price must not automatically be labeled the best supplier.

## Gate display

Use clear labels:

```text
Marketplace evidence: Passed
Sourcing evidence: Incomplete
Economics: Failed
Risk: Passed
Decision readiness: Not ready
```

Show exactly why a gate failed and what action is next.

---

# 10. Configuration

Add typed configuration for:

```text
VALIDATION_MIN_EFFECTIVE_COMPARABLES
VALIDATION_MIN_CONFIDENCE
VALIDATION_MIN_SUPPLIER_QUOTES
VALIDATION_TARGET_MARGIN_PERCENT
VALIDATION_ADVERTISING_RESERVE_PERCENT
VALIDATION_RETURNS_RESERVE_PERCENT
VALIDATION_OTHER_VARIABLE_COST_PER_UNIT
VALIDATION_MARKETPLACE_MAX_AGE_DAYS
```

Provide safe defaults in `.env.example`.

Do not hide business assumptions in calculation functions.

---

# 11. Database migrations

Create one Alembic revision after inspecting the current head.

Migration requirements:

- add all necessary enums/tables/columns;
- add foreign keys and indexes;
- add uniqueness constraints for active validation projects;
- preserve existing validation data;
- include downgrade support where practical;
- pass empty-database migration smoke tests;
- pass upgrade from the current schema.

Do not exceed the repository’s Alembic revision-ID length constraint.

---

# 12. Testing requirements

## Unit tests

Cover:

```text
status transition rules
duplicate validation prevention
RFQ placeholder generation
landed-cost calculations
tooling amortization
margin calculations
max-landed-cost calculations
missing-input behavior
gate evaluation
gate overrides
POE percentage validation
quote-state transitions
```

Use Decimal-safe assertions.

## Integration tests

Cover:

```text
start validation from a recommendation
create immutable marketplace packet
refresh marketplace packet without overwriting old versions
add three supplier quotes
calculate quote tiers
evaluate gates
approve for sample
reject project
prevent invalid transitions
```

## Regression tests

Must prove:

```text
later rescoring does not mutate the project’s original recommendation snapshot
marketplace refresh does not alter existing quotes
GET endpoints do not trigger Amazon API calls
incomplete economics never displays a precise profit value
empty risk flags do not pass the risk gate
duplicate button clicks do not create duplicate projects or RFQs
```

## Frontend tests

At minimum cover:

```text
Start validation/Open validation behavior
quote-entry form validation
gate status rendering
incomplete calculation rendering
RFQ copy/download controls
status transition confirmation
```

## Quality gates

The final implementation must pass:

```text
backend pytest
ruff
mypy
Alembic current at head
empty-database migration smoke
frontend typecheck
frontend lint
frontend production build
```

No live Amazon or supplier calls are required in CI.

---

# 13. Documentation

Add or update:

```text
README.md
docs/PRODUCT_VALIDATION_PIPELINE.md
docs/MAINTAINABILITY.md
.env.example
```

Document:

```text
the end-to-end validation workflow
which inputs are automated
which inputs are manual
calculation formulas
decision-gate rules
override behavior
why approval means “approve for sample,” not “buy inventory”
```

---

# 14. Seed/demo data

Add deterministic fixture data for one complete validation example:

```text
Product: travel cable organizer
Marketplace packet: expected price and Amazon fees
Three suppliers
Quotes at 200, 500, and 1,000 units
One viable quote
One nonviable quote
One incomplete quote
Risk evaluation
Gate evaluation
```

The demo must work without live credentials.

---

# 15. Completion report

The coding agent must provide:

```text
Summary of architecture changes
Files added
Files modified
Migration revision
API endpoints added
Frontend routes/components added
Calculation formulas implemented
Configuration added
Tests added
Command results
Known limitations
Deviations from this spec
Manual verification steps
```

The report must state explicitly whether any existing validation models were reused or replaced.

---

# Definition of done

This milestone is complete when a user can:

1. open a ranked recommendation;
2. click `Start validation`;
3. view an immutable marketplace evidence packet;
4. optionally enter Product Opportunity Explorer evidence;
5. generate and edit an RFQ;
6. manually add at least three suppliers and quantity-tier quotes;
7. see landed cost, margin, and maximum viable cost;
8. see transparent marketplace, sourcing, economics, and risk gates;
9. understand exactly what evidence is missing;
10. approve the product for samples or reject it;
11. return later and review the full audit trail.

The result should make the next action obvious without requiring the user to already be an Amazon private-label expert.
