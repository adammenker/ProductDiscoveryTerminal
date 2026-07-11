# Recommendation Engine V2

Recommendation V2 is the decision layer for product research. It is designed to keep three ideas separate:

```text
opportunity_score          how attractive the product looks
evidence_confidence_score  how much the system trusts the evidence
validation_readiness_score how close the product is to being decision-ready
```

## Opportunity Components

The opportunity score includes only product attractiveness signals:

```text
demand_proxy              30%
competition_attractiveness 30%
economics                 25%
risk / constraints        15%
```

Data quality is not an opportunity component. A well-measured weak product should not rank above a less-measured strong product merely because it has more data.

## Evidence Confidence

Evidence confidence reflects whether the product has enough trustworthy evidence to act on:

```text
source coverage
freshness
comparable relevance
historical depth
source independence
internal consistency
```

Supplier data is useful for validation, but it is not required for discovery-stage confidence. Missing supplier quotes lower readiness, not the intrinsic opportunity score.

## Validation Readiness

Readiness tracks explicit validation steps:

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

An empty risk flag list does not prove risk evaluation ran. Constraint/risk readiness requires a persisted completed evaluation with:

```text
evaluation_status = completed
evaluation_version
evaluated_at
rule_profile_id
```

## Recommendation Gating

V2 recommendations use the three scores together:

```text
high opportunity + low confidence  -> investigate or insufficient_data
high opportunity + low readiness   -> investigate
hard constraint failure            -> skip
missing supplier validation        -> cannot be fully validated pursue
stale evidence                     -> lower confidence, not opportunity
```

No-comparable cases are treated as insufficient data rather than automatic skips. Hard constraints, severe risks, and broken economics can still block a product.

## Demand Semantics

Direct demand evidence is derived from provenance, not hardcoded. Recognized direct-demand sources include manual Product Opportunity Explorer imports and other explicitly configured demand reports.

Best-seller rank evidence preserves category context. Mixed incompatible rank categories produce conflicting demand evidence and lower confidence instead of being collapsed into one confident rank.

## Competition Semantics

Offer count is treated as offer density. It is not unique seller count.

Competition attractiveness uses measured subscores only:

```text
review moat attractiveness
brand fragmentation attractiveness
offer-density attractiveness
price-dispersion attractiveness
substitute-density attractiveness
```

Missing competition inputs reduce coverage/confidence. They do not create favorable default scores.

## Fee Provenance

Every fee estimate should describe where it came from:

```text
fee_source
modeled_price_source
comparable_asin
status
confidence
```

Supported statuses:

```text
live_spapi
comparable_proxy
configured_fallback
missing
```

Configured fallback fees are low-confidence evidence and do not satisfy the same validation checks as live Product Fees estimates.

## Legacy Fields

Legacy numeric score fields are retained for API compatibility while V2 remains the source of truth. A legacy numeric zero may represent a V2 null, missing evidence, or an insufficient-data state.

Follow-up migration plan:

1. Add first-class nullable V2 persistence fields for each component value/status/confidence.
2. Backfill existing V2 JSON snapshots where possible.
3. Update API consumers to read nullable V2 fields directly.
4. Remove legacy score assumptions from UI and filters after compatibility is no longer needed.
