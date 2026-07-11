# Comparable Relevance

Comparable ASINs are the bridge between a user search term and marketplace evidence. The system must not let unrelated Amazon results drive pricing, fees, historical trends, or scoring.

## Preserved Classification Fields

Amazon observations keep discovery intent separate from marketplace classification:

```text
seed_category          user-provided or inferred search intent
amazon_category        category returned by Amazon
amazon_product_type    product type returned by Amazon
```

The seed category is not allowed to make an ASIN category-compatible by itself. Missing Amazon category/type context lowers relevance confidence.

## Relevance Statuses

```text
included            automatically accepted effective comparable
needs_review        plausible, but not strong enough for final calculations
excluded            automatically rejected
manually_included   user override; included in downstream calculations
manually_excluded   user override; excluded from downstream calculations
```

Only `included` and `manually_included` are effective comparables.

## Preliminary Relevance

Preliminary relevance runs after catalog search and before pricing. It uses conceptual signals:

```text
title similarity
product type
Amazon category
brand-specific mismatch
pack quantity
intended use
```

Clearly wrong product types are excluded before pricing calls.

## Final Relevance

Final relevance runs after pricing and adds marketplace/physical plausibility:

```text
price plausibility
dimensions
weight
material
pack size
```

Price outlier detection is robust to irrelevant products. The price median is calculated from conceptually compatible ASINs first, then final price outliers are assessed against that cleaner set.

## Canonical Access

Backend code should use `ComparableService.get_effective_comparables(product_id)` or helper methods built on it. Downstream systems should not reimplement their own inclusion filters.

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

This keeps excluded ASINs from leaking into calculations and makes manual overrides immediately visible after refresh.
