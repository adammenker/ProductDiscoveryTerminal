# Data Model

## Design Goals

The data model should support:

- multiple data sources
- noisy product names
- product aliases
- raw evidence preservation
- derived insights
- explainable scores
- cost modeling
- future plugin expansion

## Entity Overview

```text
PluginRun
  └── RawObservation
          └── ProductAlias
                  └── ProductCandidate
                          ├── MarketSignal
                          ├── SupplierSignal
                          ├── CostModel
                          ├── ProductInsight
                          └── OpportunityScore
```

## ProductCandidate

Canonical representation of a product opportunity.

Fields:

- `id`: UUID
- `canonical_name`: string
- `category`: string nullable
- `subcategory`: string nullable
- `description`: text nullable
- `status`: enum
  - candidate
  - active
  - ignored
  - archived
- `created_at`: datetime
- `updated_at`: datetime

Example:

```json
{
  "canonical_name": "facial ice roller",
  "category": "beauty",
  "status": "active"
}
```

## ProductAlias

Maps alternate names to a canonical product.

Fields:

- `id`: UUID
- `product_id`: FK ProductCandidate
- `alias`: string
- `source`: string nullable
- `confidence`: float
- `created_at`: datetime

Examples:

- ice roller
- face ice roller
- cold facial massager
- skincare ice roller

## RawObservation

Raw evidence from an ingestion source.

Fields:

- `id`: UUID
- `plugin_run_id`: FK PluginRun
- `product_id`: FK ProductCandidate nullable
- `source`: string
- `source_plugin`: string
- `observed_at`: datetime
- `entity_type`: enum
  - product
  - review
  - supplier
  - trend
  - social_post
  - marketplace_listing
  - search_result
- `external_id`: string nullable
- `title`: string nullable
- `url`: string nullable
- `raw_text`: text nullable
- `metrics`: JSONB
- `metadata`: JSONB
- `media_urls`: JSONB
- `content_hash`: string
- `created_at`: datetime

Important:

- Never overwrite raw observations.
- Use `content_hash` for deduplication.
- Preserve original source data in `metadata`.

## PluginRun

Tracks execution of ingestion or analyzer plugins.

Fields:

- `id`: UUID
- `plugin_name`: string
- `plugin_type`: enum
  - ingestion
  - analyzer
- `status`: enum
  - pending
  - running
  - success
  - partial_success
  - failed
- `started_at`: datetime
- `finished_at`: datetime nullable
- `records_created`: int
- `records_updated`: int
- `error_message`: text nullable
- `parameters`: JSONB
- `created_at`: datetime

## MarketSignal

Represents demand or competition signals.

Fields:

- `id`: UUID
- `product_id`: FK ProductCandidate
- `source`: string
- `signal_type`: enum
  - search_volume
  - search_growth
  - bestseller_rank
  - social_mentions
  - review_count
  - rating
  - price
  - seller_count
  - trend_score
- `value`: numeric
- `unit`: string nullable
- `window_start`: datetime nullable
- `window_end`: datetime nullable
- `metadata`: JSONB
- `created_at`: datetime

Examples:

```json
{
  "signal_type": "search_growth",
  "value": 32,
  "unit": "percent_90d"
}
```

## SupplierSignal

Represents manufacturing or sourcing evidence.

Fields:

- `id`: UUID
- `product_id`: FK ProductCandidate
- `source`: string
- `supplier_name`: string nullable
- `supplier_url`: string nullable
- `unit_cost`: numeric nullable
- `moq`: int nullable
- `lead_time_days`: int nullable
- `shipping_estimate`: numeric nullable
- `country`: string nullable
- `metadata`: JSONB
- `created_at`: datetime

## CostModel

Estimated unit economics for a product.

Fields:

- `id`: UUID
- `product_id`: FK ProductCandidate
- `model_name`: string
- `selling_price`: numeric
- `unit_cost`: numeric nullable
- `freight_cost_per_unit`: numeric nullable
- `packaging_cost_per_unit`: numeric nullable
- `fulfillment_cost_per_unit`: numeric nullable
- `marketplace_fee_per_unit`: numeric nullable
- `storage_cost_per_unit`: numeric nullable
- `estimated_gross_margin`: numeric nullable
- `estimated_net_margin`: numeric nullable
- `currency`: string default USD
- `assumptions`: JSONB
- `created_at`: datetime

Model names:

- fba_estimate
- three_pl_estimate
- dropship_estimate
- affiliate_estimate
- custom

## ProductInsight

Derived AI or algorithmic analysis.

Fields:

- `id`: UUID
- `product_id`: FK ProductCandidate
- `insight_type`: enum
  - review_summary
  - complaint_cluster
  - feature_gap
  - differentiation_idea
  - risk_flag
  - opportunity_thesis
  - competition_summary
- `title`: string
- `body`: text
- `confidence`: float
- `evidence_observation_ids`: JSONB
- `metadata`: JSONB
- `created_at`: datetime

## OpportunityScore

Final opportunity scoring record.

Fields:

- `id`: UUID
- `product_id`: FK ProductCandidate
- `scoring_version`: string
- `demand_score`: float
- `growth_score`: float
- `competition_score`: float
- `margin_score`: float
- `pain_point_score`: float
- `risk_score`: float
- `confidence_score`: float
- `final_score`: float
- `recommendation`: enum
  - investigate
  - watch
  - skip
  - strong_opportunity
  - needs_more_data
- `explanation`: text
- `score_breakdown`: JSONB
- `created_at`: datetime

## Relationship Notes

- One product has many observations.
- One product has many aliases.
- One product has many market signals.
- One product has many supplier signals.
- One product has many cost models.
- One product has many opportunity scores over time.
- Current score can be selected by latest `created_at` per product and scoring version.

## Indexes

Recommended indexes:

- `raw_observations.source`
- `raw_observations.entity_type`
- `raw_observations.content_hash`
- `raw_observations.observed_at`
- `product_candidates.canonical_name`
- `product_aliases.alias`
- `market_signals.product_id`
- `market_signals.signal_type`
- `supplier_signals.product_id`
- `opportunity_scores.product_id`
- `opportunity_scores.final_score`
- `plugin_runs.plugin_name`
- `plugin_runs.status`

## MVP Simplification

Use Postgres relational tables and JSONB.

Do not introduce a separate graph database for MVP.

The "product graph" is a conceptual model implemented with relational joins.
