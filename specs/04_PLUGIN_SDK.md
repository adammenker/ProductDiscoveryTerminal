# Plugin SDK

## Purpose

The plugin system is the most important extensibility point.

All source-specific data collection must live inside ingestion plugins.

All derived analysis should live inside analyzer plugins.

Core platform code should not know about Amazon, Reddit, Alibaba, TikTok, Pinterest, Etsy, or any other source.

## Plugin Types

### IngestionPlugin

Fetches data from an external or local source and returns raw observations.

Examples:

- manual CSV
- mock Amazon data
- mock Alibaba supplier data
- Reddit mentions
- Google Trends placeholder
- Etsy search results

### AnalyzerPlugin

Consumes normalized product context and produces insights/signals.

Examples:

- demand analyzer
- competition analyzer
- supplier analyzer
- economics analyzer
- review analyzer
- risk analyzer

## Ingestion Plugin Contract

```python
from typing import Protocol
from pydantic import BaseModel
from datetime import datetime

class IngestionQuery(BaseModel):
    query: str | None = None
    category: str | None = None
    limit: int = 100
    metadata: dict = {}

class RawObservationDTO(BaseModel):
    source: str
    source_plugin: str
    observed_at: datetime
    entity_type: str
    external_id: str | None = None
    title: str | None = None
    url: str | None = None
    raw_text: str | None = None
    metrics: dict = {}
    metadata: dict = {}
    media_urls: list[str] = []

class IngestionPlugin(Protocol):
    name: str
    version: str

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        ...
```

## Analyzer Plugin Contract

```python
from typing import Protocol
from pydantic import BaseModel

class ProductContext(BaseModel):
    product_id: str
    canonical_name: str
    category: str | None
    observations: list[dict]
    market_signals: list[dict]
    supplier_signals: list[dict]
    cost_models: list[dict]
    insights: list[dict]

class AnalyzerResult(BaseModel):
    market_signals: list[dict] = []
    supplier_signals: list[dict] = []
    cost_models: list[dict] = []
    insights: list[dict] = []

class AnalyzerPlugin(Protocol):
    name: str
    version: str

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        ...
```

## Plugin Manifest

Each plugin should include a manifest.

Example:

```yaml
name: manual_csv
version: 0.1.0
type: ingestion
description: Load product observations from local CSV files.
requires_auth: false
supports:
  - product
  - marketplace_listing
config_schema:
  file_path:
    type: string
    required: true
```

For MVP, the manifest can be a Python dictionary.

Later, it can become YAML.

## Plugin Directory Structure

```text
backend/app/plugins/
  ingestion/
    manual_csv/
      plugin.py
      manifest.yaml
      sample.csv
    amazon_mock/
      plugin.py
      manifest.yaml
    alibaba_mock/
      plugin.py
      manifest.yaml
    reddit_mock/
      plugin.py
      manifest.yaml
  analyzers/
    demand/
      plugin.py
    competition/
      plugin.py
    economics/
      plugin.py
    risk/
      plugin.py
    review/
      plugin.py
```

## Plugin Registry

Core service should discover plugins via a registry.

MVP approach:

```python
INGESTION_PLUGINS = [
    ManualCsvPlugin(),
    AmazonMockPlugin(),
    AlibabaMockPlugin(),
    RedditMockPlugin(),
]
```

Future approach:

- dynamic module loading
- entry points
- manifest-based discovery

## Plugin Rules

1. Plugins collect or analyze evidence.
2. Plugins do not compute final opportunity scores.
3. Plugins do not write directly to the database.
4. Plugins return DTOs to the core pipeline.
5. Plugins must be testable in isolation.
6. Plugin failures must not crash the entire run unless explicitly configured.
7. Plugins must log enough information to debug source failures.

## Initial MVP Plugins

### manual_csv

Purpose:

- Allows the entire system to be tested without external APIs.

Input CSV columns:

- title
- category
- source
- url
- price
- review_count
- rating
- raw_text
- unit_cost
- moq

### amazon_mock

Purpose:

- Simulates marketplace listing observations.

Should return:

- product title
- estimated price
- review count
- rating
- rank metadata
- URL

### alibaba_mock

Purpose:

- Simulates supplier economics.

Should return:

- supplier name
- unit cost
- MOQ
- lead time
- shipping estimate

### reddit_mock

Purpose:

- Simulates customer discussion and pain points.

Should return:

- post title
- text
- upvotes
- comments
- product mentions

### google_trends_mock

Purpose:

- Simulates demand growth.

Should return:

- keyword
- trend score
- growth percentage

## Real API Integration Policy

Do not implement real external APIs until the mock pipeline works end-to-end.

When adding real APIs:

- keep source code inside plugin folder
- add rate limiting
- add request caching
- store raw responses in observation metadata
- document authentication requirements
- document quota/cost risks
- write integration tests using recorded fixtures

## Error Handling

Each plugin run should produce a PluginRun record.

If one plugin fails:

- mark that plugin run as failed
- capture error message
- continue other plugins if possible
- show error in UI

## Rate Limiting

MVP can use simple sleep/backoff inside plugins.

Later, add a shared rate limiter service if needed.

## Authentication

MVP mock plugins require no auth.

Future plugins should read credentials from environment variables.

Never commit API keys.
