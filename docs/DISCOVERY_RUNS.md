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
```

The `/discovery` UI can override both values per run. Set `enrich_top_n` to `0` to run catalog-only discovery.

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

The default plugin list is `amazon_catalog_spapi`. Live Amazon credentials are required for live runs, but tests use fixture plugins.
