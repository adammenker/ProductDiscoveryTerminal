# Scoring Engine

## Purpose

The scoring engine turns evidence into an explainable recommendation.

It should answer:

> Is this product worth investigating?

The scoring engine should be configurable and versioned.

## Inputs

The scorer consumes:

- ProductCandidate
- MarketSignals
- SupplierSignals
- CostModels
- ProductInsights
- Risk flags
- Competition signals

## Outputs

The scorer creates an OpportunityScore.

Fields:

- demand_score
- growth_score
- competition_score
- margin_score
- pain_point_score
- risk_score
- confidence_score
- final_score
- recommendation
- explanation
- score_breakdown

## Score Range

All component scores should be normalized to 0-100.

Higher is better except `risk_score`.

For risk:

- 0 = low risk
- 100 = high risk

## MVP Formula

Use a simple weighted formula.

```text
final_score =
  0.25 * demand_score
+ 0.20 * growth_score
+ 0.20 * margin_score
+ 0.15 * pain_point_score
+ 0.10 * competition_score
- 0.20 * risk_score
```

Then clamp to 0-100.

Note:

- competition_score should represent attractiveness, not raw competition.
- high competition should lower competition_score.
- fragmented competition should raise competition_score.

## Recommendation Bands

```text
85-100: strong_opportunity
70-84: investigate
50-69: watch
30-49: needs_more_data or skip
0-29: skip
```

If confidence is low, recommendation should be `needs_more_data` even if raw score is high.

## Confidence Score

Confidence reflects data coverage.

Inputs:

- number of sources
- number of observations
- freshness
- presence of supplier data
- presence of cost model
- presence of demand signal
- presence of competition signal

MVP heuristic:

```text
confidence =
  20 if product has any observations
+ 20 if demand signals exist
+ 20 if supplier signals exist
+ 20 if cost model exists
+ 10 if review/customer pain insights exist
+ 10 if signals come from 3+ sources
```

Clamp to 100.

## Component Score Heuristics

### Demand Score

Signals:

- search volume
- marketplace rank
- social mentions
- number of observations
- product appears across multiple sources

MVP:

- low evidence: 30
- moderate evidence: 60
- high multi-source evidence: 80+

### Growth Score

Signals:

- trend increase
- rank improvement
- mention velocity
- review velocity

MVP:

- negative growth: 20
- flat: 50
- moderate growth: 70
- strong growth: 90

### Competition Score

Higher means more attractive.

Signals:

- review count of top competitors
- seller count
- concentration
- listing quality
- brand dominance

MVP:

- dominated by strong brands: 20
- many strong listings: 40
- fragmented competition: 70
- low review counts and weak listings: 85

### Margin Score

Signals:

- selling price
- estimated unit cost
- fulfillment costs
- fees
- estimated margin

MVP:

```text
net margin < 20%: 20
20-35%: 50
35-50%: 70
>50%: 90
```

### Pain Point Score

Signals:

- complaint frequency
- repeated review issues
- missing features
- low ratings despite demand

MVP:

- no complaint data: 40
- scattered complaints: 55
- repeated complaints: 75
- repeated complaints with clear fix: 90

### Risk Score

Signals:

- batteries
- supplements
- medical claims
- liquids
- fragile
- trademark terms
- high return risk
- regulatory concerns

MVP:

- simple low-risk product: 10
- fragile or size concern: 35
- battery/liquid: 60
- health/supplement/regulated: 85

## Explanation Generation

Each score must include a human-readable thesis.

Example:

```text
Facial ice roller appears worth investigating. Demand signals are rising across marketplace and trend observations. Supplier estimates suggest a low unit cost relative to a $24.99 selling price. Competition appears fragmented, and repeated review complaints mention poor cold retention and weak handles. Risk is moderate-low because the product is simple, non-electronic, and lightweight.
```

## Versioning

Each OpportunityScore must store `scoring_version`.

Initial version:

```text
mvp_v0.1
```

When formula or weights change, create a new version.

Do not overwrite old scores.

## Configurability

Weights should live in config.

Example:

```yaml
scoring_version: mvp_v0.1
weights:
  demand: 0.25
  growth: 0.20
  margin: 0.20
  pain_point: 0.15
  competition: 0.10
  risk: -0.20
```

## Future Improvements

Later versions may add:

- Bayesian scoring
- category-specific weights
- seasonality adjustment
- real FBA fee estimation
- return-rate estimates
- cash conversion cycle
- ad cost assumptions
- opportunity decay
- saturation prediction
