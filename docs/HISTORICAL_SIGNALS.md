# Historical Signals

Marketplace history is stored as snapshot cohorts. A cohort represents one logical marketplace refresh for a product's effective comparable ASINs.

## Snapshot Boundary

Snapshots are created only after successful marketplace ingestion/refresh:

```text
Amazon ingestion completes
-> comparable records synchronize
-> one snapshot cohort is created
-> scoring runs without creating snapshots
```

Read-only scoring and product-detail synchronization use `create_snapshots=False`.

## Cohort Identity

Each marketplace snapshot records:

```text
snapshot_cohort_id
product_id
comparable_asin_id
asin
observed_at
source_observation_ids
observation_fingerprint
```

The database also enforces uniqueness for:

```text
product_id
comparable_asin_id
snapshot_cohort_id
```

Retrying the same refresh does not duplicate history. New observations create a new cohort.

## Cohort vs Matched-ASIN Trends

Historical output reports two kinds of changes:

```text
cohort_change        whole-cohort aggregate change
matched_asin_change  median change for ASINs present at both endpoints
```

This prevents comparable-set churn from masquerading as a real market move. For example, if the first cohort has ASINs A/B/C and the later cohort has D/E/F, the whole-cohort price can change, but matched-ASIN price change is insufficient because there are no retained ASINs.

## Churn

Each window reports comparable churn:

```text
added_asin_count
removed_asin_count
retained_asin_count
churn_percent
```

High churn lowers historical confidence.

## Window Requirements

The 7-day, 30-day, and 90-day windows require enough actual elapsed time, enough cohorts, enough matched ASINs, and enough matched coverage. When those requirements are not met, the API returns `insufficient_history` instead of a misleading trend.

## Immutability

Historical cohorts are append-only. Late-arriving observations can create a new cohort, but they do not mutate old cohorts.
