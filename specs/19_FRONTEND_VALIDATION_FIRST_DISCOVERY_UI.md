# Frontend Validation-First Discovery UI

## Purpose

Update the UI from a generic opportunity dashboard into a validation-first discovery workflow.

The user should be guided through:

```text
discovered candidate → comparable ASINs → economics → supplier validation → constraints → evidence matrix → decision
```

## Existing UI Context

The repo already has a Next.js terminal UI with:

- dashboard
- product search
- product detail
- plugin status
- run history

Keep this structure. Add a validation workflow without removing discovery.

## New Page: Discovery Validator

Route:

```text
/validator
```

Primary user flow:

1. Enter product keyword or select existing ProductCandidate.
2. Show where the product came from: manual input, Amazon plugin, POE manual import, CSV, supplier source, etc.
3. Run Amazon comparable-ASIN research.
4. Select modeled price/comparable ASINs.
5. Calculate cost ceiling.
6. Add supplier quote.
7. Apply default rule profile.
8. Show evidence matrix and decision.

## Validator Layout

### Step 1: Product Candidate / Discovery Source

Fields:

```text
product keyword
category
candidate source
notes
target margin
```

Actions:

```text
Create candidate
Find existing product
Run discovery plugins
Run Amazon research
```

### Step 2: Comparable ASINs

Table:

```text
ASIN
title
brand
price
fees
review count if available
selected proxy
```

Actions:

```text
select / deselect comparable
refresh pricing
estimate fees
```

### Step 3: Economics

Show:

```text
modeled selling price
Amazon fees
target margin
max landed cost
sensitivity table
```

### Step 4: Supplier Quote

Form:

```text
supplier name
supplier URL
unit cost
freight per unit
packaging per unit
MOQ
lead time
country
notes
```

Show comparison:

```text
supplier landed cost vs max landed cost
```

### Step 5: Constraints

Show:

```text
passes default rule profile?
hard failures
soft warnings
```

### Step 6: Evidence Matrix + Decision

Show:

```text
pursue / investigate / watch / skip
cross-source confidence
missing evidence
opportunity thesis
```

## Product Detail Updates

Add cards:

```text
Discovery Source
Economics Validator
Supplier Validation
Constraint Fit
Evidence Matrix
Paper Trading History
```

## Dashboard Updates

Top-level dashboard should separate:

```text
Strong Opportunities
Needs Supplier Quote
Above Cost Ceiling
Constraint Failures
Watchlist
Recently Discovered
```

This is more useful than a single score ranking.

## API Client Hooks

Add hooks:

```typescript
useValidateProduct()
useComparableAsins(productId)
useSupplierQuotes(productId)
useCreateSupplierQuote(productId)
useCostCeiling(productId)
useConstraintEvaluation(productId)
useEvidenceMatrix(productId)
useCreateSnapshot(productId)
usePaperTrades()
useDiscoverySources()
```

## UI State Requirements

Every card should show:

```text
data source
last updated
confidence
missing data
```

## Warning Labels

Show warnings:

- Amazon fees are estimates from comparable ASINs.
- Supplier quotes are user-provided/manual unless source says otherwise.
- Product Opportunity Explorer data is manual import only.
- No automatic buy/sell/sourcing decision is executed.

## Acceptance Criteria

- User can discover or enter a product and validate it end-to-end.
- Product detail shows discovery/economics/supplier/constraints/evidence.
- Missing data is explicit.
- User can create a paper trade snapshot.
- UI clearly explains assumptions and missing data.
- Discovery remains visible as the beginning of the workflow.
