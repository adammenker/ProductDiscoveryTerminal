# Product Discovery Terminal — Recommendation Engine V2 and Discovery Intelligence Spec

## Purpose

This specification defines the next major implementation phase for the Product Discovery Terminal.

The project already has:

- Amazon SP-API catalog, pricing, and fee integrations
- comparable-ASIN analysis
- product scoring
- cost-ceiling calculations
- supplier quote models
- constraints and risk rules
- cross-source evidence
- paper-trading and backtesting foundations
- validator and backtesting UI pages

The next priority is not another supplier or marketplace API.

The next priority is improving the quality, defensibility, and measurability of product recommendations.

The goal of this phase is:

> Given bounded discovery inputs and Amazon marketplace data, produce a ranked list of product opportunities whose scores are explainable, whose comparable ASINs are relevant, whose missing data is handled honestly, and whose recommendations can be evaluated over time.

---

# 1. Strategic Direction

The terminal should remain a product discovery engine.

It should not become:

```text
a calculator-only tool
an Amazon Product Opportunity Explorer clone
a supplier API aggregator
an opaque score generator
```

The intended workflow is:

```text
seed categories and keywords
→ run discovery
→ cluster results into product concepts
→ select relevant comparable ASINs
→ derive demand, competition, economics, and risk signals
→ compute opportunity score
→ compute evidence confidence
→ compute validation readiness
→ generate recommendation and explanation
→ track the recommendation over time
→ compare predictions against outcomes
```

Supplier validation remains useful later, but supplier data must not be required for the discovery engine to rank products worth investigating.

---

# 2. Primary Problems to Fix

## 2.1 Missing Data Is Being Converted Into Scores

The current scoring behavior should be audited for cases where missing data becomes a neutral or favorable numeric score.

Examples of invalid behavior include:

```text
missing competition evidence → low-competition score
missing risk evidence → low-risk score
missing margin data → arbitrary margin score
missing pain-point data → arbitrary pain score
```

Missing evidence must remain missing.

It should not silently become a real score.

## 2.2 Opportunity Quality, Confidence, and Readiness Are Conflated

The application needs three separate outputs:

```text
Opportunity Score
How attractive the product appears based on available measured evidence.

Evidence Confidence
How complete, relevant, fresh, and internally consistent the evidence is.

Validation Readiness
How close the product is to a real pursue-or-skip decision.
```

Example:

```text
Opportunity Score: 82
Evidence Confidence: 68
Validation Readiness: 42
Recommendation: Investigate
Missing step: Supplier validation
```

## 2.3 Demand Is Overstated by Weak Proxies

Basic SP-API catalog and pricing data do not provide true market demand.

The application must explicitly call its output:

```text
Demand Proxy Score
```

until it incorporates direct demand data such as:

- Product Opportunity Explorer imports
- Brand Analytics reports
- historical rank movement
- historical review velocity
- historical offer-count changes
- trusted third-party demand data

## 2.4 Comparable ASINs Are Not Reliably Relevant

Amazon search results can contain multiple product types.

A broad search such as:

```text
travel organizer
```

may return:

```text
cable organizer
packing cubes
toiletry bag
passport organizer
car seat organizer
```

These must not all influence one product candidate's price, fees, competition, or demand proxies.

Comparable selection must become an explicit persisted model with automated relevance scoring and manual override.

## 2.5 Discovery Is Query-Based but Not Yet a Formal Scanning System

The current implementation supports searching known product ideas.

The next phase should formalize:

```text
seed lists
discovery runs
candidate clustering
candidate origins
run history
rejected candidate tracking
```

## 2.6 Historical Data Is Insufficient

Point-in-time values are weak signals.

The engine must start collecting immutable historical snapshots so that it can eventually calculate:

```text
price trend
offer-count trend
BSR trend
review velocity
competition growth
price compression
comparable-set churn
```

## 2.7 Scoring Has No Formal Evaluation Harness

Weights should not be tuned only by intuition.

The project needs:

```text
a labeled evaluation dataset
manual analyst feedback
ranking metrics
regression tests
false-positive analysis
false-negative analysis
score calibration reports
```

---

# 3. Scope

## In Scope

Implement:

1. Recommendation Engine V2
2. nullable and evidence-aware component scores
3. separate opportunity/confidence/readiness scores
4. redesigned demand proxy
5. redesigned competition score
6. comparable-ASIN relevance model
7. manual comparable-ASIN review
8. discovery run entities and services
9. product-concept clustering
10. historical marketplace snapshots
11. derived 7/30/90-day signals
12. recommendation evaluation harness
13. analyst feedback workflow
14. regression dataset and ranking metrics
15. cleanup of duplicate Amazon plugin paths
16. stale documentation cleanup
17. CI validation

## Out of Scope

Do not implement in this phase:

- supplier API integrations
- Alibaba automation
- 1688 automation
- automatic supplier outreach
- automated purchasing
- listing creation
- order management
- inventory management
- buyer communication
- content generation
- scraping Seller Central
- scraping Product Opportunity Explorer
- automated machine-learning model training
- external public SaaS multi-tenancy

---

# 4. Recommendation Engine V2

## 4.1 New Score Structure

Replace single-value component scores with structured component results.

Create a reusable type:

```text
ScoreComponent
- name
- value: float | null
- status
- coverage
- confidence
- evidence_count
- freshness_days
- evidence_ids
- explanation
- warnings
- metadata
```

Allowed status values:

```text
measured
inferred
missing
stale
conflicting
not_applicable
```

Example:

```json
{
  "name": "competition",
  "value": null,
  "status": "missing",
  "coverage": 15,
  "confidence": 10,
  "evidence_count": 0,
  "freshness_days": null,
  "evidence_ids": [],
  "explanation": "No relevant review-moat, offer-count, or brand-concentration evidence is available.",
  "warnings": ["Competition cannot be estimated reliably."],
  "metadata": {}
}
```

## 4.2 Missing-Data Rules

Missing values must not be replaced with favorable or neutral defaults.

Required behavior:

```text
missing component evidence
→ component value = null
→ status = missing
→ coverage decreases
→ confidence decreases
```

Do not assign values such as:

```text
missing competition = 82
missing risk = 10
missing margin = 30
missing pain points = 40
```

## 4.3 Weighted Scoring With Missing Components

Implement one of the following strategies.

Preferred strategy:

```text
Measured components retain configured weights.
Missing components are excluded.
Remaining weights are normalized.
Overall score is only generated when minimum evidence coverage is met.
```

Example:

```text
Configured weights:
Demand proxy: 30
Competition: 25
Economics: 20
Risk: 15
Data quality: 10

If risk is missing:
Normalize the remaining 85 points to 100.
Lower confidence and coverage.
Do not silently treat risk as favorable.
```

Minimum thresholds:

```text
minimum overall coverage to generate numeric opportunity score: 50
minimum confidence for investigate recommendation: 40
minimum confidence for pursue recommendation: 70
```

Values must be configurable.

## 4.4 New Top-Level Results

Every recommendation must return:

```text
opportunity_score: 0–100 | null
evidence_confidence_score: 0–100
validation_readiness_score: 0–100
recommendation
recommendation_reasons
missing_evidence
blocking_issues
next_actions
scoring_version
```

Recommendation values:

```text
pursue
investigate
watch
skip
insufficient_data
```

## 4.5 Recommendation Rules

### Pursue

Requires:

```text
opportunity_score >= configured threshold
evidence confidence >= configured threshold
validation readiness >= configured threshold
no hard constraint failures
no severe risk flags
relevant comparable ASIN set
positive modeled economics
supplier validation if enabled by current workflow
```

Until supplier validation is reintroduced as a required phase, `pursue` should either:

```text
remain disabled
```

or be labeled:

```text
pursue_research
```

Preferred MVP behavior:

```text
reserve pursue for fully validated products
use investigate for strong discovery-stage products
```

### Investigate

Use when:

```text
opportunity is attractive
evidence is sufficient for deeper research
important validation steps remain
```

### Watch

Use when:

```text
evidence is mixed
historical trend is not established
competition may be increasing
price or offer data is volatile
```

### Skip

Use when:

```text
hard constraints fail
economics are structurally weak
competition is extreme
comparables are consistently poor
risk is severe
```

### Insufficient Data

Use when:

```text
minimum score coverage is not met
comparable relevance is too weak
price/fee data are missing
evidence is too stale or conflicting
```

---

# 5. Demand Proxy V2

## 5.1 Rename Current Demand Score

Rename:

```text
demand_score
```

to:

```text
demand_proxy_score
```

Update:

- backend models
- API responses
- frontend labels
- documentation
- tests
- score explanations

## 5.2 Demand Proxy Inputs

Demand proxy may use:

```text
comparable ASIN BSR distribution
BSR coverage
historical BSR trend
historical review-count growth
historical offer-count stability
manual POE search-volume data
manual POE purchase-growth data
external trend signals
customer-pain evidence
```

Do not count source diversity as demand.

Source diversity belongs in evidence confidence.

## 5.3 BSR Aggregation

Do not use only the best observed BSR.

Calculate:

```text
median BSR
25th percentile BSR
75th percentile BSR
number of comparables with valid BSR
percentage of included comparables with BSR
BSR dispersion
category-aware normalized BSR
```

One excellent ASIN must not dominate a weak comparable set.

## 5.4 Review Data

Use:

```text
static review count
```

primarily for competition moat.

Use:

```text
review-count change over time
```

as a demand proxy.

Do not treat high static review count as pure demand evidence.

## 5.5 Direct Demand Evidence

Support manual Product Opportunity Explorer inputs where available.

Suggested normalized fields:

```text
search_volume
search_volume_growth
purchase_growth
click_share
conversion_rate
return_rate
average_price
average_review_count
top_clicked_asins
observation_date
```

Store provenance and freshness.

## 5.6 Demand Proxy Output

Example:

```json
{
  "name": "demand_proxy",
  "value": 71,
  "status": "inferred",
  "coverage": 64,
  "confidence": 58,
  "evidence_count": 14,
  "freshness_days": 2,
  "explanation": "Median BSR across 8 relevant comparables is favorable, and 30-day median BSR improved by 11%. No direct search-volume evidence is available.",
  "warnings": ["Demand is inferred from marketplace proxies."],
  "metadata": {
    "median_bsr": 18420,
    "included_comparables": 8,
    "bsr_coverage_percent": 80,
    "direct_demand_data_available": false
  }
}
```

---

# 6. Competition Score V2

## 6.1 Competition Inputs

Competition should be derived from:

```text
number of relevant close substitutes
offer count
brand concentration
dominant-brand presence
review-count distribution
rating distribution
price compression
price dispersion
low-price competitor count
comparable similarity density
seller-count trend where available
new-competitor growth over time
```

## 6.2 Missing Competition Data

If review, offer, and brand evidence are missing:

```text
competition value = null
status = missing
```

Do not produce a favorable low-competition score.

## 6.3 Brand Concentration

Calculate:

```text
number of unique brands
top-brand comparable share
top-3-brand comparable share
generic/unbranded share
```

Flag:

```text
dominant_brand_market
fragmented_brand_market
unknown_brand_concentration
```

## 6.4 Review Moat

Calculate:

```text
median review count
75th percentile review count
top-ASIN review count
percentage of comparables above review thresholds
```

Suggested configurable thresholds:

```text
100 reviews
500 reviews
1,000 reviews
5,000 reviews
```

## 6.5 Price Competition

Calculate:

```text
median price
interquartile price range
price coefficient of variation
percentage of offers within 5% of median
percentage of offers below modeled price
```

High price compression should increase competition.

## 6.6 Competition Output

Example:

```json
{
  "name": "competition",
  "value": 42,
  "status": "measured",
  "coverage": 78,
  "confidence": 72,
  "evidence_count": 11,
  "freshness_days": 1,
  "explanation": "The market has many close substitutes, but brand ownership is fragmented. Median review count is 420 and pricing is compressed within a narrow range.",
  "warnings": ["Price competition is high."],
  "metadata": {
    "included_comparables": 10,
    "unique_brands": 8,
    "median_review_count": 420,
    "price_compression_percent": 74
  }
}
```

Define score orientation clearly:

```text
high competition score = favorable low competition
```

or:

```text
high competition intensity = unfavorable
```

Preferred approach:

```text
competition_attractiveness_score
```

where a higher score is always better.

---

# 7. Economics Score V2

## 7.1 Inputs

Use:

```text
modeled selling price
comparable price range
SP-API fee estimates
price stability
default cost ceiling
target margin scenarios
size/weight risk
fee estimate confidence
```

Supplier data should not be required in this phase.

## 7.2 Output States

Possible economics status:

```text
positive_unvalidated
negative
missing_price
missing_fees
unstable_price
proxy_only
```

Example:

```text
Economics score: 74
Status: positive_unvalidated
Explanation: Amazon pricing and fee data support a positive max landed cost, but no supplier cost has been evaluated.
```

---

# 8. Evidence Confidence

## 8.1 Purpose

Evidence confidence should measure:

```text
coverage
freshness
source relevance
source independence
comparable quality
internal consistency
historical depth
```

It should not directly measure whether the product is attractive.

## 8.2 Suggested Formula

Example components:

```text
25% evidence coverage
20% comparable relevance quality
20% freshness
15% historical depth
10% source independence
10% internal consistency
```

## 8.3 Penalties

Penalize:

```text
stale observations
conflicting prices
irrelevant comparables
single-source dependence
missing fee estimates
low comparable count
high comparable dispersion
```

## 8.4 Supplier Data

Supplier data should not be required for evidence confidence during discovery-stage ranking.

Supplier data may increase:

```text
validation readiness
```

later.

---

# 9. Validation Readiness

## 9.1 Purpose

Validation readiness measures progress toward a real business decision.

Suggested checklist:

```text
relevant comparable ASIN set available
pricing data available
fee data available
constraints evaluated
risk evaluated
historical data available
direct demand evidence available
supplier quote available
supplier quote validated
IP/regulatory review complete
```

## 9.2 Discovery-Stage Readiness

Before supplier work resumes, readiness should still distinguish:

```text
raw candidate
marketplace-researched candidate
economically modeled candidate
historically tracked candidate
fully validated candidate
```

Suggested readiness stages:

```text
0–20: raw
21–40: discovered
41–60: marketplace_validated
61–80: business_validation_pending
81–100: decision_ready
```

---

# 10. Comparable ASIN Relevance

## 10.1 New Model

Add a persistent `ComparableAsin` entity.

Fields:

```text
id
product_id
asin
title
brand
product_type
category
price
currency
dimensions
weight
relevance_score
relevance_status
relevance_reasons JSON
automatic_relevance_version
manually_overridden
manual_override_reason
discovered_from_query
discovered_at
last_refreshed_at
created_at
updated_at
```

Allowed relevance statuses:

```text
included
needs_review
excluded_irrelevant
excluded_wrong_product_type
excluded_price_outlier
excluded_brand_specific
manually_included
manually_excluded
```

## 10.2 Relevance Features

Calculate relevance using:

```text
title/token similarity
normalized phrase overlap
product-type equality
category compatibility
intended-use similarity
attribute overlap
dimension similarity
weight similarity
price plausibility
brand-specific versus generic distinction
pack size / quantity compatibility
material compatibility where available
```

## 10.3 Relevance Score

Output:

```text
0–100
```

Suggested defaults:

```text
>= 75: automatically include
50–74: needs review
< 50: automatically exclude
```

Thresholds must be configurable.

## 10.4 Query Result Handling

Do not assign every Amazon result the original seed keyword as its canonical product name.

Preserve:

```text
returned ASIN title
returned product type
returned brand
returned category
returned attributes
```

Cluster or map the result to a candidate only after relevance analysis.

## 10.5 Model Input Rule

Only ASINs with status:

```text
included
manually_included
```

may contribute to:

```text
modeled price
fee range
BSR distribution
competition
review moat
brand concentration
historical trends
cost ceiling
```

## 10.6 Manual Review UI

On product detail, add a `Comparable ASIN Review` table:

```text
Include?
ASIN
Title
Brand
Product Type
Price
Relevance Score
Status
Reasons
Last Refreshed
```

Actions:

```text
include
exclude
mark needs review
reset automatic decision
```

Manual overrides must be persisted and must survive refresh runs.

## 10.7 Tests

Required regression tests:

```text
Broad keyword results should form multiple concepts.

An irrelevant product type must not affect modeled price.

A price outlier must not affect modeled price by default.

Manual inclusion must override automatic exclusion.

Manual exclusion must survive SP-API refresh.

Only included comparables feed scoring.
```

---

# 11. Discovery Runs

## 11.1 New Entities

### SeedList

```text
id
name
description
category
is_active
created_at
updated_at
```

### SeedKeyword

```text
id
seed_list_id
keyword
category
priority
status
metadata
created_at
updated_at
```

### DiscoveryRun

```text
id
seed_list_id
source_plugin
status
started_at
finished_at
parameters JSON
summary JSON
error_summary
scoring_version
created_at
```

Statuses:

```text
queued
running
completed
partial_success
failed
cancelled
```

### DiscoveryRunResult

```text
id
discovery_run_id
seed_keyword_id
source_observation_id
asin
raw_title
candidate_cluster_id
candidate_product_id
result_status
relevance_score
rejection_reason
metadata
created_at
```

### CandidateOrigin

```text
id
product_id
discovery_run_id
seed_keyword_id
source
origin_type
origin_value
first_discovered_at
last_seen_at
metadata
```

### CandidateCluster

```text
id
discovery_run_id
cluster_label
canonical_name
category
product_type
member_count
cluster_confidence
status
metadata
created_at
```

## 11.2 Discovery Run Workflow

```text
1. User selects seed list.
2. User starts discovery run.
3. Source plugin searches each keyword.
4. Raw results are stored.
5. Results are clustered into product concepts.
6. Comparable relevance is calculated.
7. Existing products are matched or new candidates are created.
8. Duplicate candidates are merged or linked.
9. Candidate origins are stored.
10. Recommendation scoring runs for eligible candidates.
11. Run summary is generated.
```

## 11.3 Candidate Clustering

Cluster returned Amazon items into distinct product concepts.

Possible inputs:

```text
title embeddings or token similarity
product type
category
brand
intended use
important attributes
pack size
dimensions
```

Do not require external embedding APIs for tests.

A deterministic token/attribute clustering baseline is acceptable for V1.

## 11.4 Discovery Result Status

Allowed values:

```text
created_candidate
matched_existing_candidate
added_comparable
rejected_irrelevant
rejected_duplicate
needs_review
failed
```

## 11.5 Discovery UI

Add:

```text
/discovery
/discovery/runs
/discovery/runs/{id}
/seed-lists
```

Dashboard sections:

```text
Recently Discovered
Needs Comparable Review
Insufficient Evidence
Top Investigate Candidates
Discovery Runs
```

## 11.6 Run Summary

Example:

```json
{
  "keywords_processed": 20,
  "raw_results": 186,
  "candidate_clusters": 42,
  "new_candidates": 18,
  "existing_candidates_updated": 9,
  "rejected_irrelevant": 71,
  "needs_review": 12,
  "failed_keywords": 1
}
```

---

# 12. Historical Marketplace Snapshots

## 12.1 Purpose

Collect immutable marketplace history for tracked products and included comparable ASINs.

## 12.2 New Model

Create:

```text
MarketplaceAsinSnapshot
- id
- product_id
- comparable_asin_id
- asin
- observed_at
- price
- featured_offer_price
- lowest_offer_price
- offer_count
- seller_count
- bestseller_rank
- bestseller_category
- review_count
- rating
- fee_estimate
- fulfillment_fee
- referral_fee
- source_observation_ids JSON
- metadata
- created_at
```

Snapshots must be immutable.

## 12.3 Refresh Policy

Support configurable refresh schedules:

```text
daily
every 3 days
weekly
manual
```

Recommended initial default:

```text
daily for top tracked candidates
every 3 days for watchlist candidates
manual for untracked candidates
```

## 12.4 Tracking Rules

Track:

```text
top N investigate candidates
manually watched candidates
paper-traded candidates
manually selected products
```

## 12.5 Derived Signals

Create a service that calculates:

```text
7-day price delta
30-day price delta
90-day price delta
price volatility
price compression trend
offer-count delta
seller-count delta
BSR delta
median comparable BSR delta
review-count delta
review velocity
rating delta
fee delta
comparable-set churn
```

## 12.6 Freshness Rules

Each signal must include:

```text
window
sample_count
coverage
latest_observation_at
status
```

Do not calculate a 30-day trend from two observations collected one day apart.

## 12.7 Historical API

Add:

```text
GET /products/{id}/history
GET /products/{id}/derived-signals
POST /products/{id}/refresh
POST /tracked-products/refresh
```

## 12.8 Historical UI

Product detail should show:

```text
Price History
BSR History
Offer Count History
Review Growth
Comparable Set Changes
Derived Trends
```

Avoid implying causality.

---

# 13. Evaluation Harness

## 13.1 Golden Dataset

Create a versioned evaluation dataset.

Preferred location:

```text
backend/evaluation/datasets/product_recommendations_v1.jsonl
```

Each record:

```json
{
  "product_name": "generic phone case",
  "category": "phone accessories",
  "input_fixture": "generic_phone_case.json",
  "human_label": "poor",
  "human_score_range": [0, 35],
  "human_reasons": [
    "extreme competition",
    "high review moat",
    "low differentiation"
  ],
  "expected_failures": [],
  "expected_warnings": [
    "dominant competition",
    "price compression"
  ]
}
```

## 13.2 Human Labels

Use:

```text
promising
uncertain
poor
insufficient_data
```

## 13.3 Analyst Feedback Model

Add:

```text
RecommendationFeedback
- id
- product_id
- recommendation_snapshot_id
- verdict
- reasons JSON
- notes
- created_at
```

Verdicts:

```text
good_recommendation
bad_recommendation
uncertain
```

Reason options:

```text
wrong_comparables
demand_overstated
demand_understated
competition_overstated
competition_understated
bad_price_estimate
bad_fee_estimate
missing_risk
missing_data_not_handled
actually_interesting
actually_unattractive
other
```

## 13.4 Evaluation Metrics

Implement:

```text
precision_at_5
precision_at_10
precision_at_20
ranking_agreement
label_accuracy
false_positive_rate
false_negative_rate
mean_score_by_human_label
score_calibration
coverage_rate
insufficient_data_rate
performance_by_category
performance_by_discovery_source
```

## 13.5 Ranking Evaluation

If human labels are ordinal:

```text
poor < uncertain < promising
```

Calculate ranking agreement using a simple rank correlation metric.

Do not require machine-learning libraries unless already installed.

## 13.6 Evaluation CLI

Add:

```bash
python -m app.evaluation.run   --dataset backend/evaluation/datasets/product_recommendations_v1.jsonl   --scoring-version recommendation_v2
```

Output:

```text
JSON report
Markdown report
console summary
```

Suggested paths:

```text
backend/evaluation/reports/
```

## 13.7 Analyst Feedback UI

Add controls on product detail:

```text
Good recommendation
Bad recommendation
Uncertain
```

Then show reason checkboxes and notes.

Feedback must not automatically alter weights in this phase.

---

# 14. Regression Tests

Add explicit regression tests for the following.

## Missing Data

```text
Missing competition evidence must not produce a favorable competition score.

Missing risk evidence must not imply low risk.

Missing economics data must not produce a confident recommendation.

Products below minimum evidence coverage must return insufficient_data.
```

## Demand

```text
One excellent BSR must not dominate ten weak comparable ASINs.

Source count must not directly increase demand proxy.

Static review count must not be treated as review velocity.

A product with improving median BSR should outrank an otherwise identical product with worsening BSR.
```

## Competition

```text
High review moat should reduce competition attractiveness.

Price compression should reduce competition attractiveness.

Fragmented brands should be more favorable than one dominant brand, all else equal.

Missing review data should lower confidence, not improve score.
```

## Comparables

```text
Irrelevant ASINs must not affect price or fee models.

Wrong product types must be excluded.

Manual include/exclude overrides must persist.

Only included comparables may feed scoring.
```

## Opportunity, Confidence, and Readiness

```text
No supplier quote must not reduce initial opportunity attractiveness.

No supplier quote may reduce validation readiness.

Stale data must lower evidence confidence.

Hard constraint failures must block pursue.

High opportunity with low confidence should produce investigate or insufficient_data, not pursue.
```

## Discovery

```text
Broad seed searches should create multiple candidate clusters.

Duplicate candidates should not be recreated across runs.

Candidate origins should record all contributing discovery runs.

Run failure for one keyword must not fail all other keywords.
```

## History

```text
Historical snapshots must be immutable.

30-day trends must require sufficient time coverage.

Late-arriving observations must not mutate old recommendation snapshots.

Derived signals must identify stale or insufficient history.
```

---

# 15. Scoring Versioning

Create a new scoring version:

```text
recommendation_v2
```

Persist scoring version on:

```text
product scores
recommendation snapshots
discovery runs
paper trades
evaluation reports
```

Do not overwrite previous scoring outputs.

Support side-by-side comparison:

```text
mvp_v0.1
recommendation_v2
```

Add a migration or backfill command if needed.

---

# 16. API Changes

## Product Detail

Extend product detail response:

```json
{
  "opportunity_score": 78,
  "evidence_confidence_score": 66,
  "validation_readiness_score": 48,
  "recommendation": "investigate",
  "scoring_version": "recommendation_v2",
  "components": {
    "demand_proxy": {},
    "competition": {},
    "economics": {},
    "risk": {},
    "data_quality": {}
  },
  "missing_evidence": [],
  "blocking_issues": [],
  "next_actions": [],
  "comparable_summary": {},
  "historical_summary": {},
  "candidate_origins": []
}
```

## New Endpoints

Add or confirm:

```text
GET /discovery/seed-lists
POST /discovery/seed-lists
PATCH /discovery/seed-lists/{id}

POST /discovery/runs
GET /discovery/runs
GET /discovery/runs/{id}

GET /products/{id}/comparables
PATCH /products/{id}/comparables/{asin}

GET /products/{id}/history
GET /products/{id}/derived-signals
POST /products/{id}/refresh

POST /products/{id}/feedback
GET /products/{id}/feedback

POST /evaluation/run
GET /evaluation/reports
GET /evaluation/reports/{id}
```

---

# 17. Frontend Changes

## 17.1 Dashboard

Show distinct sections:

```text
Top Investigate Candidates
Recently Discovered
Needs Comparable Review
Insufficient Evidence
Constraint Failures
Watchlist
Historically Improving
Historically Deteriorating
```

## 17.2 Product Detail

Required sections:

```text
Recommendation Summary
Opportunity Score
Evidence Confidence
Validation Readiness
Demand Proxy
Competition
Economics
Risk and Constraints
Comparable ASIN Review
Historical Signals
Candidate Origins
Missing Evidence
Next Actions
Analyst Feedback
Paper-Trading History
```

## 17.3 Score Labels

Never show only:

```text
Score: 82
```

Show:

```text
Opportunity: 82
Confidence: 66
Readiness: 48
Recommendation: Investigate
```

## 17.4 Missing Data

Explicitly display:

```text
Missing
Stale
Inferred
Conflicting
Measured
```

Do not render missing values as zero.

## 17.5 Comparable Review

Allow:

```text
include
exclude
review reason
reset to automatic
```

## 17.6 Discovery Run UI

Show:

```text
seed list
keywords
source
run status
raw results
candidate clusters
new candidates
duplicates
rejections
errors
```

---

# 18. Plugin Cleanup

Audit the registered Amazon plugins:

```text
amazon_sp_api
amazon_catalog_spapi
amazon_pricing_spapi
amazon_fees_spapi
```

Determine whether `amazon_sp_api` is:

```text
a legacy duplicate
an orchestrator
a distinct compatibility plugin
```

If it is a duplicate:

```text
deprecate it
remove it from default plugin registration
document migration
retain temporary compatibility only if needed
```

If it is an orchestrator:

```text
rename it clearly to amazon_spapi_research
document which split plugins it invokes
avoid double ingestion
```

Add tests preventing duplicate observations from overlapping plugin runs.

---

# 19. Documentation Cleanup

Update README and specs so they accurately describe:

```text
live SP-API catalog support
live pricing support
live fee-estimate support
recommendation_v2 scoring
discovery runs
comparable relevance
historical snapshots
supplier work being deferred
```

Remove stale statements that describe SP-API fees as future-only if they are already implemented.

Add:

```text
docs/RECOMMENDATION_ENGINE.md
docs/DISCOVERY_RUNS.md
docs/COMPARABLE_RELEVANCE.md
docs/HISTORICAL_SIGNALS.md
docs/EVALUATION.md
```

---

# 20. CI and Quality Gates

Add GitHub Actions or equivalent CI.

## Backend

Run:

```bash
pytest
ruff check app
mypy app
```

Run mypy only if configuration already exists or is added in this work.

## Database

CI must:

```text
start empty Postgres
apply all Alembic migrations
verify no migration errors
run integration tests
```

## Frontend

Run:

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
```

Run frontend tests if configured.

## End-to-End Fixture Test

Create one fixture-based end-to-end test:

```text
seed discovery run
→ create clusters
→ select relevant comparables
→ calculate recommendation_v2
→ create history snapshots
→ derive trends
→ return product detail
```

No live SP-API credentials should be needed in CI.

---

# 21. Implementation Milestones

## Milestone 1 — Recommendation Engine V2

Implement:

```text
structured nullable component scores
opportunity/confidence/readiness separation
missing-data behavior
new recommendation rules
scoring versioning
API and UI labels
```

Acceptance:

```text
missing values remain missing
products below coverage threshold return insufficient_data
supplier absence does not lower discovery opportunity
stale data lowers confidence
```

## Milestone 2 — Comparable-ASIN Relevance

Implement:

```text
ComparableAsin model
automatic relevance scoring
inclusion statuses
manual overrides
model-input filtering
comparable review UI
```

Acceptance:

```text
irrelevant ASINs no longer affect price, fees, demand, or competition
manual overrides persist
```

## Milestone 3 — Discovery Runs

Implement:

```text
SeedList
SeedKeyword
DiscoveryRun
DiscoveryRunResult
CandidateOrigin
CandidateCluster
bounded scans
candidate clustering
run UI
```

Acceptance:

```text
broad searches create multiple coherent candidate concepts
duplicate candidates are not recreated
origins are traceable
```

## Milestone 4 — Historical Signals

Implement:

```text
immutable ASIN snapshots
scheduled refresh
7/30/90-day derived signals
freshness handling
history UI
```

Acceptance:

```text
tracked candidates accumulate marketplace history
recommendation engine can consume historical trends
```

## Milestone 5 — Evaluation Harness

Implement:

```text
golden dataset
analyst feedback
evaluation CLI
ranking metrics
calibration report
regression suite
```

Acceptance:

```text
recommendation quality can be measured
false positives and false negatives are visible
weight changes can be compared by scoring version
```

## Milestone 6 — Cleanup and CI

Implement:

```text
plugin deprecation cleanup
README updates
new technical docs
GitHub Actions
empty-database migration tests
fixture-based end-to-end test
```

---

# 22. Suggested Default Scoring Weights

These are initial defaults only and must remain configurable.

```text
Demand Proxy:                  30%
Competition Attractiveness:   25%
Economics:                     20%
Risk / Constraints:           15%
Data Quality:                  10%
```

Do not include supplier validation in the initial opportunity score during this phase.

Suggested evidence confidence components:

```text
Evidence Coverage:             25%
Comparable Relevance:          20%
Freshness:                     20%
Historical Depth:              15%
Source Independence:           10%
Internal Consistency:          10%
```

Suggested readiness checklist weights:

```text
Relevant Comparables:          20%
Price Data:                    10%
Fee Data:                      10%
Constraints Evaluated:         10%
Risk Evaluated:                10%
Historical Data:               15%
Direct Demand Data:            10%
Supplier Validation:           15%
```

These defaults should be stored in versioned config rather than hardcoded into formula functions.

---

# 23. Initial Golden Test Products

Add fixtures for at least these product concepts:

```text
generic phone case
portable blender
facial ice roller
compression packing cubes
cable organizer
glass water bottle
supplement gummies
battery-powered lint remover
desk foot hammock
makeup brush cleaner
```

Expected broad behavior:

```text
generic phone case
→ competition warning
→ low ranking

portable blender
→ demand possible
→ battery/electronics/return risk
→ investigate or skip depending on evidence

facial ice roller
→ potentially investigate
→ coherent comparables required

compression packing cubes
→ potentially investigate
→ competition and review moat must be measured

glass water bottle
→ fragile risk

supplement gummies
→ hard constraint failure

battery-powered lint remover
→ battery/electronics risk

desk foot hammock
→ demand uncertainty
→ insufficient data or investigate

makeup brush cleaner
→ must distinguish manual tool from battery-powered device
```

---

# 24. Definition of Done

This phase is complete when:

- missing evidence is never converted into favorable scores
- opportunity, confidence, and readiness are separate
- demand is explicitly labeled as a proxy
- included comparable ASINs are demonstrably relevant
- irrelevant ASINs cannot affect modeled economics or scoring
- broad seed searches produce separate candidate clusters
- candidate origins are traceable
- tracked products accumulate immutable historical snapshots
- 7/30/90-day derived signals are available where enough history exists
- recommendation quality can be measured against a labeled dataset
- analyst feedback is captured
- scoring is versioned
- plugin duplication is resolved
- documentation matches the actual implementation
- CI validates backend, frontend, migrations, and a fixture-based end-to-end flow

---

# 25. Codex Execution Instructions

Codex should:

1. Read the existing repo before changing architecture.
2. Reuse existing models, services, plugins, routes, and UI components where reasonable.
3. Implement milestones incrementally.
4. Add migrations for every schema change.
5. Preserve existing SP-API functionality.
6. Preserve existing tests unless intentionally migrated.
7. Add tests before marking each milestone complete.
8. Avoid introducing paid APIs.
9. Avoid requiring live Amazon credentials in tests.
10. Stop after the milestones in this specification.

Do not implement supplier APIs as part of this assignment.
