# Evaluation Harness

The evaluation harness measures Recommendation V2 quality without retraining models or changing weights.

## Inputs

The harness uses:

```text
latest Recommendation V2 score per product
analyst feedback verdicts and reasons
optional golden labeled dataset JSON
candidate origins / discovery sources
category metadata
scoring version
```

Feedback reasons are required. Supported reasons:

```text
wrong_comparables
demand_overstated
demand_understated
competition_overstated
competition_understated
bad_price_estimate
bad_fee_estimate
missing_risk
missing_data_mishandled
actually_interesting
actually_unattractive
other
```

## Metrics

The report includes:

```text
precision@K
ranking agreement
false-positive analysis
false-negative analysis
category performance
discovery-source performance
scoring-version comparison
```

Ranking agreement is pairwise: positive labels should rank above negative labels.

## Golden Dataset Format

The default dataset is `backend/app/evaluation/golden_dataset.json`.

```json
{
  "labels": [
    {
      "canonical_name": "travel cable organizer",
      "label": "actually_interesting",
      "category": "travel accessories",
      "source": "analyst"
    }
  ]
}
```

Rows can also use `product_id` instead of `canonical_name`.

## CLI

```bash
cd backend
python -m app.evaluation --golden app/evaluation/golden_dataset.json --out evaluation_reports --k 10
```

Outputs:

```text
JSON report
Markdown report
console summary
```

The harness never automatically retrains, changes weights, or modifies recommendations.
