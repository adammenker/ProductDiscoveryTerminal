# Backtesting and Paper Trading

## Purpose

Add a feedback loop that measures whether the terminal's discovery and validation recommendations are useful.

The MVP should support product opportunity paper trading:

> Freeze recommendations today, then measure whether products improved or deteriorated 30/60/90 days later.

## Why This Matters

Without paper-trading, the score can look convincing but be unproven.

Backtesting should answer:

- Do high-score products outperform low-score products?
- Do products below supplier cost ceiling do better?
- Which constraints actually predict better outcomes?
- Which categories produce false positives?
- Which evidence sources are most predictive?
- Which discovery sources produce the best candidates?

## New Entities

### OpportunitySnapshot

A frozen copy of product state at decision time.

Fields:

```text
id
product_id
snapshot_date
snapshot_reason
discovery_source
canonical_name
category
final_score
recommendation
component_scores JSON
cost_ceiling JSON
supplier_validation JSON
constraint_evaluation JSON
evidence_matrix JSON
thesis
created_at
```

### PaperTrade

Represents a simulated decision.

Fields:

```text
id
product_id
snapshot_id
decision
hypothesis
entry_date
evaluation_windows JSON
status
created_at
```

Decisions:

```text
paper_pursue
paper_watch
paper_skip
```

### OutcomeMeasurement

Measured after a window.

Fields:

```text
id
paper_trade_id
window_days
measured_at
price_change
review_count_change
rank_change
search_interest_change
seller_count_change
supplier_cost_change
constraint_status_change
outcome_label
outcome_score
notes
metadata
```

Outcome labels:

```text
improved
flat
deteriorated
invalidated
insufficient_data
```

### BacktestRun

Aggregates results.

Fields:

```text
id
started_at
finished_at
window_days
filters JSON
metrics JSON
notes
```

## Snapshot Creation

Add button/API:

```text
POST /products/{id}/snapshots
POST /opportunities/snapshot-top
```

Snapshot top creates snapshots for top N current opportunities.

Example:

```json
{
  "limit": 20,
  "min_score": 70,
  "decision": "paper_pursue"
}
```

## Outcome Measurement

For MVP, allow manual outcome entry.

Add endpoint:

```text
POST /paper-trades/{id}/outcomes
```

Later, outcome measurement can be automated via refreshed Amazon/pricing/trend plugins.

## Backtest Metrics

Generate:

```text
precision_at_k
top_decile_average_outcome
bottom_decile_average_outcome
rank_correlation
false_positive_categories
false_negative_categories
source_predictiveness
constraint_predictiveness
discovery_source_quality
```

MVP can implement simple metrics:

```text
top_picks_improved_rate
watch_picks_improved_rate
skip_picks_improved_rate
average_outcome_by_recommendation
average_outcome_by_discovery_source
```

## UI Requirements

Add page:

```text
/backtests
```

Sections:

- Open paper trades
- Snapshots waiting for 30/60/90-day evaluation
- Outcome entry form
- Backtest summary
- False positives
- False negatives
- Discovery source performance

Product detail page should show:

```text
Paper Trading History
```

## Scoring Improvement Loop

Do not auto-retrain scoring in MVP.

Instead, generate insight:

```text
Products with supplier quote below ceiling improved 62% of the time.
Products without supplier quotes improved 28% of the time.
Beauty tools had high false-positive rate due to competition increases.
Manual POE imports outperformed raw Amazon keyword discoveries.
```

## Tests

Add tests for:

- create opportunity snapshot
- snapshot freezes current score/evidence
- create paper trade
- add outcome measurement
- aggregate backtest metrics
- product detail returns paper history
- no future data mutates old snapshot

## Acceptance Criteria

- User can snapshot product recommendations.
- User can create paper pursue/watch/skip decisions.
- User can manually record 30/60/90-day outcomes.
- Backtest page reports whether recommendations performed.
- Old snapshots are immutable.
- Backtest can report quality by discovery source.
