from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SeedKeywordCreate(BaseModel):
    keyword: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeedListCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    keywords: list[SeedKeywordCreate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeedKeywordResponse(BaseModel):
    id: str
    seed_list_id: str
    keyword: str
    category: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SeedListResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    keywords: list[SeedKeywordResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DiscoveryKeywordInput(BaseModel):
    keyword: str = Field(min_length=2, max_length=255)
    category: str | None = Field(default=None, max_length=120)


class DiscoveryRunCreate(BaseModel):
    seed_list_id: str | None = None
    keywords: list[DiscoveryKeywordInput] = Field(default_factory=list)
    plugins: list[str] | None = None
    limit_per_keyword: int = Field(default=10, ge=1, le=50)


class CandidateClusterResponse(BaseModel):
    id: str
    seed_keyword_id: str | None = None
    label: str
    normalized_key: str
    source_query: str
    representative_title: str | None = None
    evidence_observation_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryRunResultResponse(BaseModel):
    id: str
    seed_keyword_id: str | None = None
    candidate_cluster_id: str
    product_id: str
    product_name: str
    status: str
    rank_position: int | None = None
    opportunity_score: float | None = None
    recommendation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateOriginResponse(BaseModel):
    id: str
    product_id: str
    discovery_run_id: str
    seed_keyword_id: str | None = None
    candidate_cluster_id: str | None = None
    source_plugin: str
    source_query: str
    source_observation_id: str | None = None
    source_external_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiscoveryRunResponse(BaseModel):
    id: str
    seed_list_id: str | None = None
    status: str
    source_plugins: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    clusters: list[CandidateClusterResponse] = Field(default_factory=list)
    results: list[DiscoveryRunResultResponse] = Field(default_factory=list)
    origins: list[CandidateOriginResponse] = Field(default_factory=list)
