# V2 Correctness Hardening Spec

## Status

Ready for implementation.

## Suggested Repository Path

```text
specs/21_V2_CORRECTNESS_HARDENING.md
```

## Objective

Harden the Product Discovery Terminal V2 implementation before adding supplier APIs or expanding discovery sources.

The current V2 architecture is directionally correct, but several data-integrity and scoring issues can make rankings, historical trends, and confidence values misleading.

This work should make the engine trustworthy enough for manual Amazon product research by ensuring:

1. Marketplace snapshots are idempotent.
2. Historical trends compare equivalent cohorts.
3. Amazon observations preserve correct semantics.
4. Comparable-ASIN filtering happens before expensive downstream requests.
5. Opportunity score, confidence, and readiness remain conceptually separate.
6. Only effective comparables influence scoring and history.
7. Repository documentation, CI, and plugin registration match the current implementation.

Do not add supplier APIs as part of this spec.

---

# 1. Required Implementation Order

Implement milestones in this exact order:

```text
Milestone 1 — Snapshot Idempotency
Milestone 2 — Historical Cohort Correctness
Milestone 3 — Amazon Signal Semantics
Milestone 4 — Comparable-ASIN Pipeline Ordering
Milestone 5 — Scoring Decoupling and Readiness Fixes
Milestone 6 — Canonical Effective-Comparable Access
Milestone 7 — Repository Cleanup and CI
Milestone 8 — Discovery Runs
Milestone 9 — Evaluation Harness
```

Milestones 1–7 are required for this assignment.

Milestones 8–9 should be implemented only after 1–7 are complete and all acceptance criteria pass.

---

# 2. Non-Goals

Do not implement:

- Alibaba API integration
- 1688 integration
- supplier scraping
- supplier outreach
- automated purchasing
- inventory management
- listing creation
- order management
- buyer communication
- content generation
- machine-learning model training
- Seller Central scraping
- Product Opportunity Explorer scraping
- public multi-tenant authentication

---

# 3. Milestone 1 — Snapshot Idempotency

## Problem

Marketplace snapshots may be created from multiple code paths, including:

```text
Amazon refresh
comparable synchronization
pipeline execution
product rescoring
```

Rescoring without new Amazon observations must not create new marketplace history.

Duplicate snapshots distort:

- sample counts
- price trends
- BSR trends
- offer-count trends
- review velocity
- database size

## Required Changes

### 3.1 Define One Snapshot Creation Boundary

Snapshots must be created only after a successful marketplace refresh or ingestion event.

Required flow:

```text
Amazon ingestion completes
→ comparable records synchronize
→ one snapshot cohort is created
→ scoring runs without creating snapshots
```

All scoring and read-only synchronization paths must use:

```python
create_snapshots=False
```

or an equivalent explicit mode.

### 3.2 Add Snapshot Cohort Identity

Add a refresh-level or cohort-level identifier.

Preferred field:

```text
snapshot_cohort_id
```

A cohort represents one logical refresh of a product's comparable ASINs.

Each snapshot should include:

```text
snapshot_cohort_id
product_id
comparable_asin_id
asin
observed_at
source_observation_ids
```

### 3.3 Add Idempotency Protection

Use one of these approaches:

```text
Database uniqueness constraint
or
service-level upsert with deterministic fingerprint
```

Preferred unique identity:

```text
unique(
  product_id,
  comparable_asin_id,
  snapshot_cohort_id
)
```

If source observations already provide a stable retrieval identity, additionally store:

```text
observation_fingerprint
```

### 3.4 Required Tests

Add tests:

```text
Rescoring a product without new observations creates zero new snapshots.

One marketplace refresh creates exactly one snapshot cohort.

Retrying the same refresh does not duplicate snapshots.

A new marketplace refresh creates a new cohort.

Scoring can run after refresh without mutating history.
```

## Acceptance Criteria

- Snapshot creation occurs in one canonical service path.
- Rescoring is read-only with respect to historical snapshots.
- Duplicate snapshot insertion is prevented at both application and database levels.
- Existing product-detail history remains readable.

---

# 4. Milestone 2 — Historical Cohort Correctness

## Problem

Historical deltas must not compare different comparable-ASIN compositions as though they were the same market.

Incorrect example:

```text
Early snapshots contain ASINs A, B, C.
Later snapshots contain ASINs D, E, F.
The engine reports a price increase.
```

That apparent change may come entirely from comparable-set churn.

## Required Changes

### 4.1 Calculate Cohort Aggregates

For every snapshot cohort, calculate:

```text
median price
median featured offer
median BSR
median review count
median offer count
included comparable count
coverage percentage
```

Store or derive these aggregates by cohort.

### 4.2 Calculate Matched-ASIN Changes

For every requested window:

```text
Find ASINs present in both endpoint cohorts.
Calculate each ASIN's individual change.
Take the median of those changes.
```

Return:

```text
matched_asin_count
starting_cohort_size
ending_cohort_size
matched_coverage_percent
```

### 4.3 Return Both Trend Types

Historical API output should distinguish:

```json
{
  "cohort_change": {},
  "matched_asin_change": {},
  "comparable_churn": {}
}
```

Example:

```json
{
  "price": {
    "cohort_change_percent": 8.4,
    "matched_asin_change_percent": 3.1,
    "matched_asin_count": 7,
    "matched_coverage_percent": 70,
    "status": "measured"
  }
}
```

### 4.4 Minimum Window Requirements

Do not calculate a 30-day signal unless:

```text
endpoint timestamps span approximately 30 days
minimum matched ASIN count is satisfied
minimum coverage is satisfied
minimum snapshot count is satisfied
```

Return:

```text
insufficient_history
```

when requirements are not met.

### 4.5 Comparable Churn

Calculate:

```text
added ASIN count
removed ASIN count
retained ASIN count
churn percentage
```

High churn should lower historical confidence.

### 4.6 Required Tests

Add tests:

```text
Composition-only changes do not appear as matched-ASIN price changes.

Matched-ASIN trends use only ASINs present at both endpoints.

High comparable churn lowers trend confidence.

30-day trends require sufficient time span.

Historical snapshots remain immutable.

Late-arriving observations do not mutate old cohorts.
```

## Acceptance Criteria

- Trend calculations are cohort-aware.
- Matched-ASIN and whole-cohort trends are reported separately.
- Insufficient history is explicit.
- Comparable churn is visible in API responses and UI.

---

# 5. Milestone 3 — Amazon Signal Semantics

## 5.1 Offer Count vs Seller Count

### Problem

Offer count and seller count must not be treated as equivalent.

### Required Change

Persist:

```text
offer_count
```

when the API provides number of offers.

Persist:

```text
seller_count = null
```

unless unique sellers are actually measured.

Competition scoring may use offer count as:

```text
offer density
```

It must not label it as unique seller count.

### Tests

```text
offer_count is never copied into seller_count.

Missing seller_count remains null.

Competition explanations distinguish offers from sellers.
```

---

## 5.2 Bestseller Rank Category Context

### Problem

Raw BSR values from different categories are not directly comparable.

### Required Change

Persist all useful rank observations with:

```text
rank
rank_category
browse_node
classification
observed_at
```

Do not collapse mixed-category BSRs into one confident demand proxy.

Required behavior:

```text
consistent rank category
→ measured or inferred demand proxy

mixed incompatible rank categories
→ status = conflicting
→ confidence penalty
```

### Tests

```text
Mixed BSR categories produce conflicting evidence.

BSR aggregation preserves category labels.

One favorable leaf-category rank cannot dominate unrelated ranks.
```

---

## 5.3 Seed Category vs Amazon Category

### Problem

User-provided search intent must not masquerade as marketplace classification.

### Required Fields

Keep separate:

```text
seed_category
amazon_category
amazon_product_type
```

Comparable relevance must use:

```text
amazon_category
amazon_product_type
returned attributes
```

The seed category should be used only as discovery intent.

### Tests

```text
Seed category does not automatically make an ASIN category-compatible.

Returned Amazon category is preserved.

Missing Amazon category lowers relevance confidence.
```

---

## 5.4 Fee Estimate Provenance

Every fee estimate must include:

```text
fee_source
modeled_price_source
comparable_asin
status
confidence
```

Required statuses:

```text
live_spapi
comparable_proxy
configured_fallback
missing
```

Example:

```json
{
  "fee_source": "amazon_product_fees",
  "modeled_price_source": "configured_default",
  "status": "configured_fallback",
  "confidence": "low"
}
```

Configured fallback fees must not appear equivalent to live ASIN-based fee estimates.

### Tests

```text
Configured fallback fee estimates are labeled low confidence.

Live Product Fees estimates outrank fallback estimates.

Missing price data cannot silently create a high-confidence fee estimate.
```

---

## 5.5 Raw Payload Retention

Add configuration:

```env
STORE_RAW_AMAZON_PAYLOADS=false
RAW_PAYLOAD_RETENTION_DAYS=7
```

Default behavior should retain:

```text
normalized fields
request or response identifiers
retrieval timestamp
schema version
compact diagnostic metadata
```

Do not store full raw responses indefinitely unless explicitly enabled.

---

# 6. Milestone 4 — Comparable-ASIN Pipeline Ordering

## Problem

Pricing and fee API calls should not be spent on obviously irrelevant catalog results.

## Required Two-Pass Workflow

Implement:

```text
1. Catalog search
2. Preliminary conceptual relevance
3. Exclude clearly wrong product types
4. Fetch pricing for included and needs-review ASINs
5. Recalculate relevance with price and physical attributes
6. Fetch fees only for final included ASINs
7. Persist one snapshot cohort
8. Run Recommendation V2 scoring
```

## Preliminary Relevance Inputs

Use:

```text
title similarity
product type
Amazon category
brand-specific mismatch
pack quantity
intended use
```

## Final Relevance Inputs

Add:

```text
price plausibility
dimensions
weight
material
pack size
```

## Robust Price Filtering

Do not derive price outliers from a median contaminated by clearly irrelevant products.

Required approach:

```text
Phase A:
conceptual compatibility

Phase B:
robust price median and MAD/IQR among Phase A survivors
```

## API Call Rules

```text
Catalog calls:
all search results

Pricing calls:
included + needs-review after preliminary relevance

Fee calls:
final included comparables only
```

Manual inclusion must allow a user to request pricing/fees for an automatically excluded ASIN.

## Required Tests

```text
Wrong product types do not receive fee requests.

Clearly irrelevant catalog results are filtered before pricing.

Price outliers are detected using conceptually compatible ASINs only.

Manual inclusion can trigger downstream pricing and fees.

Excluded ASINs do not affect modeled price or fees.
```

## Acceptance Criteria

- API usage is reduced for irrelevant results.
- Comparable relevance is applied before downstream economics.
- Manual overrides remain authoritative.
- Snapshot cohorts include only effective comparables.

---

# 7. Milestone 5 — Scoring Decoupling and Readiness Fixes

## 7.1 Remove Data Quality From Opportunity Score

### Problem

Data quality is already represented by Evidence Confidence.

Including it in Opportunity Score makes well-measured products look intrinsically more attractive.

### Required Opportunity Components

Use:

```text
Demand Proxy
Competition Attractiveness
Economics
Risk / Constraints
```

Remove:

```text
Data Quality
```

from opportunity weights.

Evidence quality must affect:

```text
evidence_confidence_score
recommendation gating
```

not product attractiveness.

---

## 7.2 Evidence Confidence

Evidence confidence should use:

```text
coverage
freshness
comparable relevance
historical depth
source independence
internal consistency
```

Supplier data must not be required for discovery-stage evidence confidence.

---

## 7.3 Validation Readiness

Readiness should evaluate completion of explicit steps.

Suggested checks:

```text
relevant comparable set
pricing available
fee estimate available
constraint evaluation completed
risk evaluation completed
historical depth available
direct demand evidence available
supplier validation available
```

Supplier absence may reduce readiness.

Supplier absence must not reduce initial opportunity attractiveness.

---

## 7.4 Direct Demand Availability

Do not hardcode:

```text
direct_demand_available = false
```

Derive it from evidence provenance.

Recognized direct-demand sources may include:

```text
manual Product Opportunity Explorer import
approved Brand Analytics report import
other explicitly configured direct-demand source
```

Demand component metadata should include:

```json
{
  "direct_demand_available": true,
  "direct_demand_sources": []
}
```

---

## 7.5 Risk Evaluation Completion

An empty `risk_flags` list does not prove that risk analysis ran.

Require explicit persisted state:

```text
evaluation_status = completed
evaluation_version
evaluated_at
rule_profile_id
```

Only a completed evaluation earns readiness credit.

---

## 7.6 Competition Scoring

Replace favorable starting baselines with independently measured subscores:

```text
review moat attractiveness
brand fragmentation attractiveness
offer-density attractiveness
price-dispersion attractiveness
substitute-density attractiveness
```

Weight only measured subscores.

Missing competition inputs must lower coverage and confidence, not improve competition attractiveness.

---

## 7.7 Recommendation Gating

Required behavior:

```text
High opportunity + low confidence
→ investigate or insufficient_data

High opportunity + low readiness
→ investigate

Hard constraint failure
→ skip

Missing supplier validation
→ cannot produce fully validated pursue

Stale data
→ lower confidence, not necessarily opportunity
```

## Required Tests

```text
Data completeness does not directly raise opportunity score.

Supplier absence does not lower opportunity score.

Supplier absence lowers readiness only.

Direct-demand evidence increases readiness.

Empty risk flags without completed evaluation earn no readiness points.

High opportunity with low confidence cannot produce pursue.

Missing competition evidence does not create favorable competition score.
```

---

# 8. Milestone 6 — Canonical Effective-Comparable Access

## Problem

Excluded comparables must not influence any downstream calculation.

## Required Service

Create one canonical method:

```python
get_effective_comparables(product_id)
```

It must return only:

```text
included
manually_included
```

All downstream code must use this method.

Required consumers:

```text
modeled pricing
fee selection
BSR aggregation
competition scoring
evidence confidence
historical trends
cost ceiling
snapshot creation
product detail summaries
```

Do not independently reimplement inclusion filtering in multiple services.

## Required Tests

```text
Excluded comparables never affect price.

Excluded comparables never affect fees.

Excluded comparables never affect BSR.

Excluded comparables never affect competition.

Excluded comparables never affect confidence.

Excluded comparables never appear in snapshot cohorts.

Manual inclusion immediately affects downstream models after refresh.
```

---

# 9. Milestone 7 — Repository Cleanup and CI

## 9.1 Amazon Plugin Registration

Audit:

```text
amazon_sp_api
amazon_catalog_spapi
amazon_pricing_spapi
amazon_fees_spapi
```

Determine whether `amazon_sp_api` is:

```text
legacy duplicate
orchestrator
compatibility alias
```

Required outcome:

- If duplicate: deprecate and remove from defaults.
- If orchestrator: rename to `amazon_spapi_research` and document child plugins.
- Prevent double ingestion.

Add tests proving one research run does not insert duplicate observations.

---

## 9.2 Legacy Scoring

The repository may temporarily retain legacy fields for compatibility, but V2 must remain the source of truth.

Document:

```text
legacy numeric zero may represent V2 null
```

Create a follow-up migration plan for first-class nullable V2 persistence.

Do not expand legacy scoring logic.

---

## 9.3 Generated Files

Remove generated package metadata:

```text
*.egg-info/
```

Add to `.gitignore`:

```gitignore
*.egg-info/
```

---

## 9.4 README and Documentation

Update README to accurately describe:

```text
live SP-API catalog integration
live pricing integration
live fee integration
Recommendation V2
comparable relevance
historical snapshots
supplier integrations deferred
```

Remove stale statements saying live Product Fees support is future work.

Add or update:

```text
docs/RECOMMENDATION_ENGINE_V2.md
docs/AMAZON_RESEARCH_PIPELINE.md
docs/COMPARABLE_RELEVANCE.md
docs/HISTORICAL_SIGNALS.md
```

---

## 9.5 CI

Add GitHub Actions.

### Backend

Run:

```bash
pytest
ruff check app
mypy app
```

Run mypy only if configured.

### Database

CI must:

```text
start empty PostgreSQL
apply all Alembic migrations
run migration smoke test
run integration tests
```

### Frontend

Run:

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
```

### End-to-End Fixture Test

Add a fixture-only flow:

```text
catalog fixture
→ preliminary relevance
→ pricing fixture
→ final relevance
→ fees fixture
→ one snapshot cohort
→ Recommendation V2
→ product detail response
```

No live Amazon credentials are allowed in CI.

## Acceptance Criteria

- CI passes from a clean clone.
- Empty-database migrations pass.
- Frontend builds successfully.
- One fixture-based Amazon research flow completes end-to-end.
- Documentation matches current behavior.

---

# 10. Milestone 8 — Formal Discovery Runs

Implement this only after Milestones 1–7 are complete.

## Required Models

```text
SeedList
SeedKeyword
DiscoveryRun
DiscoveryRunResult
CandidateOrigin
CandidateCluster
```

## Required Workflow

```text
seed list
→ bounded Amazon searches
→ raw result persistence
→ product-concept clustering
→ candidate creation or matching
→ comparable relevance
→ recommendation scoring
→ run summary
```

## Important Rule

A broad query must be able to produce multiple candidate concepts.

Example:

```text
travel organizer
```

may produce:

```text
travel cable organizer
hanging toiletry bag
compression packing cubes
passport organizer
```

Do not collapse all results into one product candidate.

## Required Tests

```text
Broad queries create multiple coherent clusters.

Duplicate candidates are not recreated across runs.

Candidate origins preserve every contributing run.

One failed keyword does not fail the entire run.

Discovery results are traceable back to seed and source.
```

---

# 11. Milestone 9 — Evaluation Harness

Implement this only after Milestones 1–8 are complete.

## Required Components

```text
golden labeled dataset
analyst feedback reasons
evaluation CLI
precision@K
ranking agreement
false-positive analysis
false-negative analysis
category performance
discovery-source performance
scoring-version comparison
```

## Feedback Reasons

Frontend feedback must capture reasons:

```text
wrong comparables
demand overstated
demand understated
competition overstated
competition understated
bad price estimate
bad fee estimate
missing risk
missing data mishandled
actually interesting
actually unattractive
other
```

A verdict without reasons is insufficient for tuning.

## Required Output

Generate:

```text
JSON report
Markdown report
console summary
```

Do not automatically retrain or modify weights.

---

# 12. Required Database Migrations

Add Alembic migrations for all schema changes.

Likely additions:

```text
snapshot_cohort_id
observation_fingerprint
rank category fields
risk evaluation completion fields
direct demand provenance fields
plugin deprecation metadata if needed
discovery-run models in Milestone 8
```

Every migration must:

```text
upgrade from current main
work on an empty database
include downgrade where practical
avoid destructive data loss
```

---

# 13. Required API Behavior

## Product Detail

Return:

```json
{
  "opportunity_score": 78,
  "evidence_confidence_score": 66,
  "validation_readiness_score": 48,
  "recommendation": "investigate",
  "components": {},
  "effective_comparables": [],
  "historical_signals": {},
  "missing_evidence": [],
  "blocking_issues": [],
  "next_actions": []
}
```

## Historical Signals

Return:

```json
{
  "window_days": 30,
  "cohort_change": {},
  "matched_asin_change": {},
  "comparable_churn": {},
  "status": "measured",
  "confidence": 72
}
```

## Missing Values

Never serialize missing numeric evidence as a fabricated zero unless the API schema explicitly distinguishes:

```text
value = null
status = missing
```

---

# 14. Frontend Requirements

## Product Detail

Show:

```text
Opportunity
Confidence
Readiness
Recommendation
Comparable Review
Fee Provenance
Historical Cohort Trends
Matched-ASIN Trends
Comparable Churn
Missing Evidence
Next Actions
```

## History Labels

Clearly distinguish:

```text
Whole-cohort change
Matched-ASIN change
```

## Evidence Status

Display:

```text
Measured
Inferred
Missing
Stale
Conflicting
Fallback
```

## Dashboard

Use V2 as the single source of truth.

Suggested buckets:

```text
Investigate
Watch
Skip
Insufficient Data
Needs Comparable Review
Historically Improving
Historically Deteriorating
```

Do not derive top-level buckets from legacy supplier or economics fields when V2 recommendation is available.

---

# 15. Full Regression Checklist

Codex must add or confirm tests for all of the following:

```text
Rescoring without new observations creates no snapshots.

One refresh creates exactly one cohort.

Retrying a refresh is idempotent.

Historical trends compare matched ASINs correctly.

Cohort composition changes do not masquerade as product changes.

Excluded comparables affect no downstream calculations.

offer_count is not copied into seller_count.

Mixed BSR categories produce conflicting evidence.

Seed category does not replace Amazon category.

Fee fallback provenance is explicit.

Data quality does not raise opportunity attractiveness.

Supplier absence lowers readiness, not opportunity.

Direct demand evidence increases readiness.

Empty risk flags do not prove completed risk evaluation.

Wrong product types are filtered before fee requests.

Manual comparable overrides persist.

Duplicate Amazon plugins do not duplicate observations.

Empty-database migrations pass.

Fixture-based end-to-end research passes without live credentials.
```

---

# 16. Completion Report

When implementation is complete, Codex must provide:

```text
1. Summary of changes
2. Files added
3. Files modified
4. Migrations added
5. Tests added
6. Commands run
7. Test results
8. Known limitations
9. Deferred work
10. Any deviations from this spec
```

Codex must not claim completion if:

```text
tests are failing
migrations do not apply cleanly
snapshot idempotency is unverified
historical trend logic remains composition-biased
excluded comparables still affect scoring
```

---

# 17. Definition of Done

Milestones 1–7 are complete when:

- Rescoring creates no marketplace snapshots.
- One refresh produces one idempotent cohort.
- Historical changes use cohort-aware and matched-ASIN calculations.
- Offer count and seller count are no longer conflated.
- BSR retains category context.
- Seed and Amazon categories are separate.
- Fee fallbacks are explicitly labeled.
- Relevance filtering occurs before pricing and fees where possible.
- Opportunity excludes data-quality weighting.
- Confidence and readiness use correct semantics.
- Risk and direct-demand readiness are evidence-driven.
- One canonical effective-comparable function feeds all models.
- Duplicate Amazon plugin behavior is resolved.
- README and technical docs are current.
- CI passes from a clean clone.
- Fixture-based end-to-end Amazon research works without live credentials.

After that, proceed to formal discovery runs and the evaluation harness.
