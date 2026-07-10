# Custom Constraints and Risk Rules

## Purpose

Make the terminal opinionated around the user's actual product constraints.

Amazon Product Opportunity Explorer is generic. This terminal should be personalized.

Custom constraints improve discovery by filtering out products that might look attractive generally but are bad fits for this user.

The app should support hard filters and soft scoring rules like:

- no batteries
- no supplements
- no liquids
- no fragile glass
- small/lightweight preferred
- selling price $20-$50
- target net margin >= 30%
- max landed cost <= configurable threshold
- low return-risk products preferred
- no restricted/regulatory categories

## New Concept: Rule Profile

Add a user-editable `RuleProfile`.

MVP can store a single default profile in config or DB.

Fields:

```text
id
name
is_default
hard_rules JSON
soft_rules JSON
created_at
updated_at
```

Example hard rules:

```json
{
  "exclude_batteries": true,
  "exclude_supplements": true,
  "exclude_liquids": true,
  "exclude_fragile_glass": true,
  "min_selling_price": 20,
  "max_selling_price": 50,
  "min_target_margin": 30
}
```

Example soft rules:

```json
{
  "prefer_weight_under_lb": 1.5,
  "prefer_review_count_under": 500,
  "prefer_moq_under": 1000,
  "penalize_brand_dominance": true
}
```

## Risk Flag Extraction

Extend risk analyzer to generate structured risk flags:

```text
battery
liquid
supplement
medical_claim
fragile
oversized
electronics
children_product
skin_contact
food_contact
trademark_brand_risk
high_return_risk
seasonal
```

Each risk flag should include:

```text
risk_type
severity
confidence
evidence
source
```

## Constraint Evaluation

Add:

```text
ConstraintEvaluation
```

or store in ProductInsight metadata.

Fields:

```text
product_id
rule_profile_id
hard_failures
soft_warnings
constraint_score
eligible
explanation
created_at
```

Decision:

```text
eligible = no hard failures
```

## Scoring Integration

If a product violates hard rules:

```text
final recommendation cannot be strong_opportunity
```

If violation is severe:

```text
recommendation = skip
```

Soft warnings reduce score but do not block.

## UI Requirements

Add filter controls:

```text
Hide products with hard-rule failures
Only show eligible products
Show no-battery products
Show lightweight only
Selling price range
Target margin
```

On product detail show:

```text
Constraint Fit
- Eligible: yes/no
- Hard failures
- Soft warnings
- Rule profile used
- Explanation
```

## Backend API

Add:

```text
GET /rule-profiles
GET /rule-profiles/{id}
POST /rule-profiles
PATCH /rule-profiles/{id}
POST /products/{id}/evaluate-constraints
```

MVP may skip profile editing UI and use a default config file if faster.

## Default Rule Profile

Create default profile:

```text
Adam Conservative FBA Filter
```

Rules:

```text
exclude batteries
exclude supplements
exclude ingestibles
exclude liquids
exclude fragile glass
exclude weapons / restricted products
prefer products under 1.5 lb
prefer selling price $20-$50
prefer MOQ <= 1000
target margin >= 30%
```

## Tests

Add tests for:

- battery product hard fails
- supplement product hard fails
- liquid product hard fails
- product with no flags passes
- soft rules reduce constraint score
- hard failure blocks strong_opportunity
- API returns constraint evaluation
- filters hide ineligible products

## Acceptance Criteria

- Products are evaluated against default rule profile.
- Ineligible products are visibly marked.
- Scoring respects hard failures.
- User can filter by eligibility.
- Risk flags include evidence, not just labels.
