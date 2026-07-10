# Cost Ceiling Engine V2

## Purpose

Upgrade the current cost ceiling engine from a single calculated value into a validation engine that produces:

- max landed cost
- break-even landed cost
- required supplier unit cost
- margin-of-safety
- sensitivity table
- pass/fail recommendation
- explanation

This is one of the strongest differentiators versus Amazon Product Opportunity Explorer.

Discovery finds candidates. Cost ceiling validation tells the user what supplier economics must be true for the candidate to be viable.

## Existing Repo Context

The repo already has `backend/app/economics/cost_ceiling.py`, and README documents this formula:

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

Keep this formula as the core, but make the system more useful.

## New Output Requirements

For each product, generate cost ceilings for multiple target margins:

```text
20%
30%
40%
50%
```

For each margin scenario, calculate:

```text
selling_price
amazon_fees
inbound_cost_per_unit
storage_estimate
return_allowance
ad_allowance
target_profit
break_even_landed_cost
max_landed_cost
required_supplier_unit_cost
supplier_landed_cost
margin_of_safety
margin_of_safety_percent
estimated_profit_after_allowances
estimated_profit_margin_after_allowances
decision
```

## Decision Values

Use:

```text
needs_supplier_quote
quote_at_or_below_ceiling
quote_above_ceiling
insufficient_amazon_fee_data
insufficient_price_data
invalid_negative_ceiling
```

## Cost Source Priority

When calculating Amazon fees, use this source order:

1. `amazon_spapi_product_fees` CostModel
2. manually entered Amazon fee estimate
3. Keepa/third-party imported fee estimate if later added
4. current configurable defaults

The CostModel metadata must store:

```text
fee_source
fee_source_confidence
comparable_asin
assumptions_used
```

## Sensitivity Table

Create a `CostSensitivityResult` object.

Inputs:

```text
selling prices: low / modeled / high
target margins: 20 / 30 / 40 / 50
fee estimates: low / modeled / high
```

Output:

A matrix of max landed costs.

Example:

| Price | Target Margin | Low Fees | Modeled Fees | High Fees |
|---|---:|---:|---:|---:|
| $19.99 | 30% | $5.10 | $4.40 | $3.80 |
| $24.99 | 30% | $8.20 | $7.55 | $6.90 |

## Data Model

Prefer storing the sensitivity table in CostModel metadata rather than creating many new tables.

Example:

```json
{
  "cost_ceiling_v2": {
    "modeled": {...},
    "sensitivity": [...],
    "source_priority": ["amazon_spapi_product_fees", "defaults"],
    "selected_fee_source": "amazon_spapi_product_fees"
  }
}
```

## Scoring Integration

Cost ceiling should affect margin/economics score.

Suggested rules:

```text
No supplier quote:
  economics score is based on whether max landed cost is realistically positive.

Supplier quote at/below ceiling:
  boost margin score.

Supplier quote above ceiling:
  penalize margin score heavily.

Negative max landed cost:
  mark opportunity as skip or invalid economics.
```

## UI Requirements

On product detail page, add a section:

```text
Economics Validator
```

Show:

- modeled price
- fee source
- target margin selector
- max landed cost
- supplier landed cost if present
- margin of safety
- sensitivity table
- decision badge
- assumptions used

The UI should explicitly answer:

```text
To hit a 30% margin, you need fully landed cost ≤ $X/unit.
```

## API Requirements

Product detail endpoint should include:

```json
{
  "economics_validator": {
    "modeled": {},
    "sensitivity": [],
    "assumptions": {},
    "fee_source": "amazon_spapi_product_fees",
    "warnings": []
  }
}
```

## Tests

Add tests for:

- multiple target margins
- live fee source beats default fee source
- negative ceiling produces invalid decision
- supplier below ceiling passes
- supplier above ceiling fails
- required supplier unit cost handles freight + packaging
- sensitivity table values are rounded consistently
- product detail API exposes economics validator

## Acceptance Criteria

- User can see exact max landed cost at 20/30/40/50% margin.
- System clearly states the assumptions used.
- Supplier quotes can be compared against the ceiling.
- Product score penalizes products that fail economics.
- Existing single-value cost ceiling tests still pass or are migrated.
