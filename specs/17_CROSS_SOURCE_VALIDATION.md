# Cross-Source Validation

## Purpose

Avoid building an Amazon-only clone of Product Opportunity Explorer.

The terminal should synthesize evidence across discovery and validation sources:

- Amazon comparable ASINs
- Amazon pricing/fees
- supplier quotes
- manual Product Opportunity Explorer candidate input
- Reddit/social/manual trend notes
- Google Trends mock/future data
- manual CSV imports
- future Keepa or other third-party imports

The goal is to answer:

> Do independent data sources agree that this discovered candidate is worth investigating?

## New Concept: Evidence Matrix

For each product, produce an `EvidenceMatrix`.

Rows:

```text
Discovery Source
Amazon Demand
Amazon Competition
Amazon Pricing
Amazon Fees
Supplier Quotes
Customer Pain
Trend/Social Interest
Constraint Fit
Backtest/Paper History
```

Columns:

```text
signal
source_count
strength
direction
freshness
confidence
evidence_links
notes
```

Direction values:

```text
positive
neutral
negative
mixed
missing
```

## Cross-Source Score

Add a `cross_source_confidence_score`.

Suggested heuristic:

```text
+20 Amazon comparable ASINs found
+15 Amazon pricing data available
+15 Amazon fee estimate available
+20 supplier quote available
+10 supplier quote below ceiling
+10 customer pain evidence exists
+10 trend/social/manual external evidence exists
+10 constraints pass
-20 evidence conflict
-20 stale data
```

Clamp 0-100.

## Opportunity Thesis Upgrade

Current scoring explains scores. Upgrade thesis to include source agreement.

Good thesis:

```text
This product was discovered from manual/marketplace input and validated against Amazon comparable ASINs. Comparable ASINs indicate a viable $24.99-$29.99 price range. Product Fees estimates imply max landed cost of $6.40/unit at 30% target margin. Two supplier quotes are below this ceiling. Customer pain observations repeatedly mention poor cold retention. The product passes the default no-battery/no-liquid constraints. Cross-source confidence is high.
```

Bad thesis:

```text
This scored 87 because demand_score was high.
```

## Product Opportunity Explorer Input

Do not scrape Seller Central.

Add a manual import path:

```text
product_opportunity_explorer_manual_csv
```

Accepted columns:

```text
niche
search_volume
search_volume_growth
purchase_growth
average_price
average_review_count
return_rate
top_clicked_asins
notes
```

If user manually exports/copies allowed data, this plugin can ingest it.

Store as RawObservation with source:

```text
amazon_product_opportunity_explorer_manual
```

## API Requirements

Product detail should include:

```json
{
  "evidence_matrix": [
    {
      "area": "Amazon Pricing",
      "direction": "positive",
      "strength": 82,
      "confidence": 76,
      "source_count": 3,
      "freshness_days": 2,
      "notes": "Comparable ASINs support $24.99 modeled price."
    }
  ],
  "cross_source_confidence_score": 78
}
```

## UI Requirements

Add section:

```text
Evidence Matrix
```

Show a dense table with:

- area
- direction badge
- strength
- confidence
- freshness
- source count
- notes

Add a `Missing Evidence` subsection:

```text
Need supplier quote
Need fee estimate
Need non-Amazon trend signal
Need customer pain evidence
```

## Scoring Integration

Final recommendation rules:

```text
strong_opportunity requires:
- passing constraints
- positive economics
- at least one viable supplier quote
- Amazon price/fee data or manual substitute
- cross_source_confidence_score >= 70
```

`investigate` can be used when discovery evidence is promising but validation evidence is incomplete.

`watch` is used for mixed or incomplete evidence.

`skip` is used for economics failure, constraints failure, or strongly negative evidence.

## Tests

Add tests for:

- evidence matrix generation
- missing evidence detection
- cross-source score
- manual Product Opportunity Explorer import
- thesis includes evidence matrix conclusions
- strong_opportunity blocked if supplier quote missing
- score decreases when evidence is stale or conflicting

## Acceptance Criteria

- Product detail explains source agreement/disagreement.
- Missing evidence is explicit.
- Manual Product Opportunity Explorer input can be imported.
- Strong opportunities require more than discovery demand.
