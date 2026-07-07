# Pipeline Orchestration

## Key Decision

The MVP uses **scheduled batch processing**, not event-driven infrastructure.

This is a personal side project and should avoid unnecessary cloud cost and complexity.

## Pipeline Summary

```text
Trigger pipeline
  ↓
Create run record
  ↓
Run ingestion plugins
  ↓
Persist raw observations
  ↓
Normalize observations into products
  ↓
Run analyzer plugins
  ↓
Compute opportunity scores
  ↓
Expose results in UI
```

## Trigger Modes

MVP should support:

1. Manual trigger from API:
   - `POST /ingestion/run`

2. Manual trigger from UI:
   - "Run pipeline" button

3. Optional scheduled trigger:
   - APScheduler interval
   - daily run
   - hourly run for local testing if desired

## Do Not Use Initially

Do not use:

- Kafka
- SQS
- SNS
- Lambda fan-out
- Step Functions
- distributed Celery clusters
- Kubernetes
- separate worker fleet

## Pipeline Stages

### Stage 1: Create Pipeline Run

Create a parent run object or reuse PluginRun records.

Store:

- start time
- requested plugins
- parameters
- status

### Stage 2: Run Ingestion Plugins

For each enabled ingestion plugin:

1. Load plugin.
2. Build `IngestionQuery`.
3. Call `plugin.fetch(query)`.
4. Validate returned DTOs.
5. Deduplicate by content hash.
6. Persist RawObservation records.
7. Record success/failure.

### Stage 3: Normalize Observations

For each new raw observation:

1. Extract candidate product name.
2. Clean title.
3. Infer category if possible.
4. Match existing ProductAlias.
5. If no match, create ProductCandidate.
6. Create ProductAlias if useful.
7. Link observation to product.

MVP can use simple string matching.

Recommended MVP matching:

- lowercase
- remove punctuation
- remove stop words
- singularize basic plurals
- fuzzy match against existing aliases

Avoid overengineering entity resolution in v1.

### Stage 4: Run Analyzer Plugins

For each updated product:

1. Build ProductContext.
2. Run enabled analyzer plugins.
3. Persist MarketSignals, SupplierSignals, CostModels, and ProductInsights.
4. Record analyzer plugin runs.

Analyzer plugins should be idempotent where possible.

### Stage 5: Compute Opportunity Score

For each updated product:

1. Gather latest signals.
2. Compute score components.
3. Generate explanation.
4. Persist OpportunityScore.

### Stage 6: Refresh UI

The UI reads from API.

No special refresh infrastructure is needed.

## Idempotency

Pipeline should be safe to rerun.

Strategies:

- content hashes for observations
- unique constraints where practical
- timestamped score records
- avoid destructive updates
- store new score versions instead of overwriting history

## Batch Size

MVP defaults:

- 100 observations per plugin run
- 50 products analyzed per pipeline run
- configurable limits

## Run Status

Statuses:

- pending
- running
- success
- partial_success
- failed

Use `partial_success` if some plugins fail but others complete.

## Logging

Log:

- plugin start/end
- number of records fetched
- number of records inserted
- normalization count
- analyzer output count
- scoring count
- errors

## Cost Controls

- Default to mock plugins.
- Add API plugins one at a time.
- Cache external API responses.
- Allow per-plugin run limits.
- Allow plugins to be disabled.
- Store run duration and record count.
- Later, add cost estimates per plugin.

## Future Migration Path

If the project grows, each stage can become an event:

```text
RawObservationCreated
ProductNormalized
ProductAnalyzed
OpportunityScored
```

But do not implement event infrastructure until there is a real scale problem.
