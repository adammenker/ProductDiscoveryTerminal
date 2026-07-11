# Discovery Runs

Discovery runs turn broad seed keywords into multiple product concepts. They are intentionally separate from the single-product research search.

## Workflow

```text
seed list
-> bounded Amazon catalog searches
-> raw observation persistence
-> product-concept clustering
-> candidate creation or matching
-> comparable relevance
-> preliminary Recommendation V2 scoring
-> top-N candidate enrichment
-> final Recommendation V2 scoring and ranking
-> run summary
```

`POST /discovery/runs` creates a queued run and returns immediately. A single in-process worker picks up queued discovery runs one at a time, updates `status` plus `summary.progress_stage` / `summary.progress_percent`, and the `/discovery` UI polls the run list while work is active.

Broad queries may produce several candidates. For example, `travel organizer` can cluster into:

```text
travel cable organizer
hanging toiletry bag
compression packing cube
passport organizer wallet
```

## Traceability

The discovery schema records:

```text
SeedList
SeedKeyword
DiscoveryRun
CandidateCluster
DiscoveryRunResult
CandidateOrigin
```

Each result is traceable back to the seed keyword, source plugin, source query, cluster, product candidate, and source observation when a raw observation was inserted.

## Duplicate Handling

Candidates are matched by normalized aliases before creating new products. Repeated runs should add origins/results without recreating duplicate product candidates.

If raw observations are deduplicated because the same Amazon result was already stored, the discovery service falls back to existing observations for the same source query so the new run still keeps origin traceability.

## Bounded Enrichment

Discovery does not fully enrich every raw cluster. That would burn through SP-API calls too quickly.

Instead, each run:

```text
scores candidates preliminarily
filters clusters below the minimum confidence threshold
selects the top N remaining candidates
runs the full Amazon refresh flow for those candidates
reranks the final discovery results
```

The full refresh flow is:

```text
Catalog -> preliminary relevance -> Pricing -> final relevance -> Fees -> snapshots -> analyzers -> scoring
```

Defaults:

```env
DISCOVERY_ENRICH_TOP_N=20
DISCOVERY_MIN_CLUSTER_CONFIDENCE=0.60
DISCOVERY_ENRICHMENT_REQUEST_INTERVAL_SECONDS=2.0
DISCOVERY_ENRICH_MAX_PER_SOURCE_QUERY=3
DISCOVERY_ENRICH_MAX_PER_OPPORTUNITY=1
```

The `/discovery` UI can override the top-N and confidence values per run. Set `enrich_top_n` to `0` to run catalog-only discovery. Candidates are selected round-robin across source queries and capped per opportunity, preventing one niche or a set of listing variants from consuming the enrichment budget. `DISCOVERY_ENRICHMENT_REQUEST_INTERVAL_SECONDS` adds a pause between full Amazon refreshes, while the SP-API client separately paces catalog, pricing, and fee operations.

Final results are ranked as opportunity concepts. Brand, color, size, material, and pack variants collapse beneath a representative candidate, while accessories remain separate. Every score includes `data_readiness` (`catalog_only`, `partially_enriched`, `amazon_enriched`, or `validated`) and incomplete evidence receives a visible score factor before ranking.

## API

```text
POST /discovery/seed-lists
GET  /discovery/seed-lists
POST /discovery/runs
GET  /discovery/runs
GET  /discovery/runs/{run_id}
```

Example run:

```bash
curl -X POST http://localhost:8000/discovery/runs \
  -H 'Content-Type: application/json' \
  -d '{"keywords":[{"keyword":"travel organizer"}],"limit_per_keyword":10,"enrich_top_n":20,"min_cluster_confidence":0.6}'
```

The create response may have `status: "queued"` or `status: "running"`. Poll `GET /discovery/runs/{run_id}` or refresh the `/discovery` page to follow progress through catalog scan, preliminary scoring, enrichment, and final ranking.

The default plugin list is `amazon_catalog_spapi`. Live Amazon credentials are required for live runs, but tests use fixture plugins.
