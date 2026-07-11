from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class IngestionQuery(BaseModel):
    query: str | None = None
    category: str | None = None
    limit: int = 100
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawObservationDTO(BaseModel):
    source: str
    source_plugin: str
    observed_at: datetime
    entity_type: str
    external_id: str | None = None
    title: str | None = None
    url: str | None = None
    raw_text: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    media_urls: list[str] = Field(default_factory=list)


class ProductContext(BaseModel):
    product_id: str
    canonical_name: str
    category: str | None = None
    observations: list[dict[str, Any]] = Field(default_factory=list)
    market_signals: list[dict[str, Any]] = Field(default_factory=list)
    supplier_signals: list[dict[str, Any]] = Field(default_factory=list)
    cost_models: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)


class AnalyzerResult(BaseModel):
    market_signals: list[dict[str, Any]] = Field(default_factory=list)
    supplier_signals: list[dict[str, Any]] = Field(default_factory=list)
    cost_models: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)


class IngestionPlugin(Protocol):
    name: str
    version: str
    manifest: dict[str, Any]

    def fetch(self, query: IngestionQuery) -> list[RawObservationDTO]:
        ...


class AnalyzerPlugin(Protocol):
    name: str
    version: str
    manifest: dict[str, Any]

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        ...


class PluginInfo(BaseModel):
    name: str
    version: str
    enabled: bool = True
    type: str
    description: str | None = None
    supports: list[str] = Field(default_factory=list)
    configured: bool | None = None
    environment: str | None = None
    missing_credentials: list[str] = Field(default_factory=list)


class PluginRunSummary(BaseModel):
    id: str | None = None
    plugin_name: str
    plugin_type: str | None = None
    status: str
    records_created: int = 0
    records_updated: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PluginCatalog(BaseModel):
    ingestion: list[PluginInfo]
    analyzers: list[PluginInfo]


class PipelineRunRequest(BaseModel):
    plugins: list[str] | None = None
    query: IngestionQuery = Field(default_factory=IngestionQuery)
    run_analyzers: bool = True
    score: bool = True


class PipelineRunResponse(BaseModel):
    status: str
    plugin_runs: list[PluginRunSummary]
    products_updated: int
    scores_updated: int
    observations_created: int
    errors: list[str] = Field(default_factory=list)
    message: str | None = None


class ProductResearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=120)


class ProductResearchResponse(BaseModel):
    product_id: str
    canonical_name: str
    category: str | None = None
    created: bool
    pipeline: PipelineRunResponse
