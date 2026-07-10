# Supplier Validation Workflow

## Purpose

Build a supplier validation layer that answers:

> Can this discovered product actually be sourced below the required max landed cost?

This should be supplier-source agnostic. Alibaba is just one possible source.

## Existing Repo Context

The repo already supports supplier-related data through:

- `alibaba_mock`
- disabled `alibaba_open_api`
- `manual_csv` optional supplier columns:
  - unit_cost
  - moq
  - lead_time_days
  - shipping_estimate
  - supplier_name
  - country
- Supplier analyzer plugin
- Cost ceiling engine

Do not block on Alibaba official API.

## New Concept: SupplierQuote

Add a normalized supplier quote model or represent it through SupplierSignal + metadata.

Preferred model if adding a table:

```text
SupplierQuote
- id
- product_id
- source
- supplier_name
- supplier_url
- quote_date
- unit_cost
- freight_cost_per_unit
- packaging_cost_per_unit
- moq
- lead_time_days
- country
- currency
- quote_status
- confidence
- notes
- metadata
- created_at
```

Quote statuses:

```text
raw
parsed
needs_review
validated
rejected
expired
```

## Ingestion Paths

Implement these first:

### 1. Manual CSV supplier import

Enhance `manual_csv` to accept:

```text
supplier_name
supplier_url
unit_cost
freight_cost_per_unit
packaging_cost_per_unit
moq
lead_time_days
country
quote_date
currency
supplier_notes
```

### 2. Pasted supplier quote import

Add a simple backend endpoint:

```text
POST /supplier-quotes/import-text
```

Input:

```json
{
  "product_id": "...",
  "source": "manual_paste",
  "text": "Supplier ABC: $2.80/unit, MOQ 500, freight $0.70/unit..."
}
```

MVP parser can be simple regex + manual review fields.

### 3. Alibaba manual URL import

Add:

```text
supplier_alibaba_manual
```

This does not scrape.

It lets the user paste:

```text
Alibaba listing URL
supplier name
unit cost
MOQ
lead time
shipping notes
```

## Validation Against Cost Ceiling

For each supplier quote, calculate:

```text
supplier_landed_cost =
  unit_cost
  + freight_cost_per_unit
  + packaging_cost_per_unit
```

Compare to selected cost ceiling:

```text
margin_of_safety = max_landed_cost - supplier_landed_cost
```

Decision:

```text
quote_at_or_below_ceiling
quote_above_ceiling
needs_supplier_quote
```

## Supplier Score

Add a supplier validation score:

```text
supplier_validation_score
```

Suggested heuristic:

```text
100 = multiple validated quotes below ceiling
80 = one quote below ceiling with reasonable MOQ
60 = quote near ceiling within 10%
40 = quote above ceiling but negotiable
20 = no supplier quote
0 = quotes far above ceiling
```

Penalize:

- huge MOQ
- long lead time
- missing freight estimate
- suspiciously low quote
- quote older than 90 days
- high shipping complexity

## Product Detail UI

Add section:

```text
Supplier Validation
```

Show:

- supplier quotes table
- landed cost
- max landed cost
- margin of safety
- MOQ
- lead time
- status
- quote age
- confidence
- source

Add badges:

```text
Below Ceiling
Near Ceiling
Above Ceiling
Needs Quote
Expired
```

## New API Endpoints

```text
GET /products/{id}/supplier-quotes
POST /products/{id}/supplier-quotes
PATCH /supplier-quotes/{id}
DELETE /supplier-quotes/{id}
POST /supplier-quotes/import-text
```

## Opportunity Score Integration

Supplier validation should heavily affect final recommendation.

Rules:

```text
Strong discovery evidence + no supplier quote:
  recommendation = investigate, not strong_opportunity.

Strong discovery evidence + supplier below ceiling:
  eligible for strong_opportunity.

Strong discovery evidence + all suppliers above ceiling:
  recommendation = skip or watch.

Supplier quote below ceiling but weak demand:
  recommendation = watch / investigate, not strong_opportunity.
```

## Tests

Add tests for:

- manual CSV supplier quote ingestion
- pasted quote parsing
- supplier landed cost calculation
- supplier below/above ceiling decision
- quote older than threshold is expired
- supplier validation score
- product scoring changes after quote added
- UI/API returns supplier validation section

## Acceptance Criteria

- User can manually add supplier quotes.
- System calculates landed cost per quote.
- System compares quotes against cost ceilings.
- Product recommendations reflect whether sourcing is viable.
- No Alibaba API access is required.
