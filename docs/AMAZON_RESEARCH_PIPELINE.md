# Amazon Research Pipeline

Amazon research is orchestrated by `AmazonRefreshPipeline`. The default research UI and `/ingestion/research` endpoint should use this pipeline rather than invoking child plugins independently.

## Active Plugins

```text
amazon_catalog_spapi   Catalog Items search
amazon_pricing_spapi   Competitive pricing and offer-count evidence
amazon_fees_spapi      Product Fees estimates
```

The old combined `amazon_sp_api` plugin is treated as a legacy duplicate and is not registered in the default plugin catalog. This prevents one research run from double-ingesting the same Amazon evidence.

## Two-Pass Flow

```text
1. Catalog search
2. Preliminary comparable relevance
3. Exclude clearly wrong product types
4. Fetch pricing for included and needs-review ASINs
5. Recalculate relevance with price and physical attributes
6. Fetch fees only for final included ASINs
7. Persist one marketplace snapshot cohort
8. Run analyzer plugins and Recommendation V2 scoring
```

This ordering avoids spending pricing and Product Fees calls on obviously irrelevant catalog results.

## API Call Rules

Catalog calls receive the user keyword/query.

Pricing calls receive only comparable ASINs with preliminary status:

```text
included
needs_review
manually_included
```

Fee calls receive only final effective comparables:

```text
included
manually_included
```

Excluded ASINs do not influence modeled price, fee selection, BSR aggregation, competition scoring, evidence confidence, historical snapshots, or cost ceilings.

## Manual Overrides

Manual inclusion is authoritative. When a user marks an ASIN as `manually_included`, the product refresh runs again so downstream pricing and fee evidence can be requested for that ASIN.

Manual exclusion removes the ASIN from effective comparable calculations even if it previously looked relevant.

## Raw Payload Retention

By default, Amazon observations store normalized fields, request diagnostics, retrieval timestamp, schema version, and compact metadata. Full raw Amazon payloads are not retained unless explicitly enabled:

```env
STORE_RAW_AMAZON_PAYLOADS=false
RAW_PAYLOAD_RETENTION_DAYS=7
```

This keeps local diagnostics useful without retaining full marketplace responses indefinitely.

## Connectivity and CI

Live credentials are never required in CI. The fixture-based test flow uses fake catalog, pricing, and fees plugins:

```text
catalog fixture
-> preliminary relevance
-> pricing fixture
-> final relevance
-> fees fixture
-> one snapshot cohort
-> Recommendation V2
-> product detail response
```

For a local live connectivity smoke test, use the opt-in SP-API connectivity test:

```bash
docker compose exec -T \
  -e AMAZON_SP_API_CONNECTIVITY_TEST=1 \
  backend python -m pytest app/tests/test_amazon_sp_api_connectivity.py -q
```

That test exchanges the configured refresh token and performs a read-only lookup. It does not ingest product records.
