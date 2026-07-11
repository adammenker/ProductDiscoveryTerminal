from __future__ import annotations

import re
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    CandidateCluster,
    CandidateOrigin,
    DiscoveryRun,
    DiscoveryRunResult,
    OpportunityScore,
    ProductAlias,
    ProductCandidate,
    ProductStatus,
    RawObservation,
    SeedKeyword,
    SeedList,
)
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.pipeline.ingestion_runner import IngestionRunner
from app.plugins.registry import get_ingestion_plugins
from app.schemas.discovery import DiscoveryRunCreate, SeedListCreate
from app.schemas.plugin import IngestionPlugin, IngestionQuery, PipelineRunResponse
from app.services.comparable_service import ComparableService
from app.services.normalization_service import normalize_alias
from app.services.scoring_service import ScoringService

DEFAULT_DISCOVERY_PLUGINS = ["amazon_catalog_spapi"]
CONCEPT_STOP_WORDS = {
    "amazon",
    "best",
    "black",
    "blue",
    "case",
    "for",
    "green",
    "kit",
    "large",
    "new",
    "pack",
    "portable",
    "red",
    "set",
    "small",
    "the",
    "with",
}
GENERIC_PRODUCT_TYPES = {"base_product", "baseproduct", "product", "item"}


@dataclass
class KeywordSpec:
    keyword: str
    category: str | None = None
    seed_keyword_id: uuid.UUID | None = None


class DiscoveryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def create_seed_list(self, payload: SeedListCreate) -> SeedList:
        name = _clean(payload.name)
        seed_list = SeedList(
            name=name,
            description=payload.description,
            metadata_=payload.metadata,
        )
        self.db.add(seed_list)
        self.db.flush()
        seen: set[str] = set()
        for keyword in payload.keywords:
            cleaned = _clean(keyword.keyword)
            if cleaned in seen:
                continue
            seen.add(cleaned)
            self.db.add(
                SeedKeyword(
                    seed_list_id=seed_list.id,
                    keyword=cleaned,
                    category=_clean(keyword.category) if keyword.category else None,
                    metadata_=keyword.metadata,
                )
            )
        self.db.commit()
        self.db.refresh(seed_list)
        return seed_list

    def list_seed_lists(self) -> list[SeedList]:
        return list(self.db.scalars(select(SeedList).order_by(SeedList.created_at.desc())))

    def list_runs(self, limit: int = 25) -> list[DiscoveryRun]:
        return list(
            self.db.scalars(
                select(DiscoveryRun)
                .order_by(DiscoveryRun.started_at.desc())
                .limit(max(1, min(limit, 100)))
            )
        )

    def get_seed_list(self, seed_list_id: uuid.UUID | str) -> SeedList | None:
        return self.db.get(SeedList, uuid.UUID(str(seed_list_id)))

    def get_run(self, run_id: uuid.UUID | str) -> DiscoveryRun | None:
        return self.db.get(DiscoveryRun, uuid.UUID(str(run_id)))

    def run_discovery(
        self,
        payload: DiscoveryRunCreate,
        *,
        plugin_overrides: list[IngestionPlugin] | None = None,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None = None,
    ) -> DiscoveryRun:
        keywords = self._keyword_specs(payload)
        plugin_names = payload.plugins or DEFAULT_DISCOVERY_PLUGINS
        plugins = plugin_overrides if plugin_overrides is not None else get_ingestion_plugins(plugin_names)
        found = {plugin.name for plugin in plugins}
        missing_plugins = sorted(set(plugin_names) - found)
        run = DiscoveryRun(
            seed_list_id=uuid.UUID(payload.seed_list_id) if payload.seed_list_id else None,
            status="running",
            started_at=datetime.now(UTC),
            source_plugins=[plugin.name for plugin in plugins],
            parameters=payload.model_dump(),
            summary={},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        enrich_top_n = self._enrich_top_n(payload, plugin_overrides, refresh_pipeline_factory)
        min_cluster_confidence = (
            float(payload.min_cluster_confidence)
            if payload.min_cluster_confidence is not None
            else float(self.settings.discovery_min_cluster_confidence)
        )

        errors = [f"Unknown ingestion plugin: {name}" for name in missing_plugins]
        product_ids: set[uuid.UUID] = set()
        observations_created = 0
        clusters_created = 0
        origins_created = 0
        candidates_created = 0
        candidates_matched = 0
        keyword_successes = 0

        ingestion_runner = IngestionRunner(self.db)
        for keyword in keywords:
            keyword_had_result = False
            for plugin in plugins:
                query = IngestionQuery(
                    query=keyword.keyword,
                    category=keyword.category,
                    limit=payload.limit_per_keyword,
                    metadata={
                        "discovery_run_id": str(run.id),
                        "seed_keyword_id": str(keyword.seed_keyword_id)
                        if keyword.seed_keyword_id
                        else None,
                    },
                )
                plugin_run = ingestion_runner.run_plugin(plugin, query)
                observations_created += plugin_run.records_created
                if plugin_run.error_message:
                    errors.append(f"{keyword.keyword} / {plugin.name}: {plugin_run.error_message}")
                observations = self._observations_for_run_or_keyword(
                    plugin_run_id=plugin_run.id,
                    source_plugin=plugin.name,
                    keyword=keyword.keyword,
                )
                clusters = self._cluster_observations(keyword, observations)
                for cluster_key, cluster_observations in clusters.items():
                    product, created = self._match_or_create_product(
                        cluster_key.label,
                        cluster_observations,
                    )
                    cluster_confidence = _cluster_confidence(cluster_key, cluster_observations)
                    cluster = CandidateCluster(
                        discovery_run_id=run.id,
                        seed_keyword_id=keyword.seed_keyword_id,
                        label=cluster_key.label,
                        normalized_key=cluster_key.normalized_key,
                        source_query=keyword.keyword,
                        representative_title=cluster_key.representative_title,
                        evidence_observation_ids=[str(observation.id) for observation in cluster_observations],
                        metadata_={
                            "observation_count": len(cluster_observations),
                            "created_product": created,
                            "cluster_method": cluster_key.method,
                            "cluster_confidence": cluster_confidence,
                            "enrichment_eligible": cluster_confidence >= min_cluster_confidence,
                        },
                    )
                    self.db.add(cluster)
                    self.db.flush()
                    clusters_created += 1
                    if created:
                        candidates_created += 1
                    else:
                        candidates_matched += 1
                    product_ids.add(product.id)
                    keyword_had_result = True
                    for observation in cluster_observations:
                        observation.product_id = product.id
                        if self._create_origin(run, keyword, cluster, product, observation):
                            origins_created += 1
                self.db.commit()
            if keyword_had_result:
                keyword_successes += 1

        preliminary_scores = self._sync_and_score(product_ids)
        enrichment_candidates = self._enrichment_candidates(
            run=run,
            scores=preliminary_scores,
            limit=enrich_top_n,
            min_cluster_confidence=min_cluster_confidence,
        )
        enrichment = self._enrich_products(
            enrichment_candidates,
            refresh_pipeline_factory=refresh_pipeline_factory,
        )
        errors.extend(enrichment["errors"])
        scores = self._latest_scores(product_ids)
        results_created = self._create_results(run, scores)
        status = _status(
            keyword_count=len(keywords),
            keyword_successes=keyword_successes,
            errors=errors,
            results_created=results_created,
        )
        run.status = status
        run.finished_at = datetime.now(UTC)
        run.error_message = "; ".join(errors)[:2000] if errors else None
        run.summary = {
            "keywords_requested": len(keywords),
            "keywords_succeeded": keyword_successes,
            "keywords_failed": len(keywords) - keyword_successes,
            "plugins_requested": plugin_names,
            "plugins_run": [plugin.name for plugin in plugins],
            "observations_created": observations_created,
            "clusters_created": clusters_created,
            "origins_created": origins_created,
            "candidates_created": candidates_created,
            "candidates_matched": candidates_matched,
            "rejected_results": 0,
            "products_matched_or_created": len(product_ids),
            "results_created": results_created,
            "enrichment_top_n": enrich_top_n,
            "min_cluster_confidence": min_cluster_confidence,
            "enrichment_candidates": len(enrichment_candidates),
            "enrichment_requested": enrichment["requested"],
            "enriched_candidates": enrichment["completed"],
            "enrichment_failed": enrichment["failed"],
            "enrichment_observations_created": enrichment["observations_created"],
            "enrichment_errors": enrichment["errors"],
            "enriched_product_ids": [str(product_id) for product_id in enrichment["product_ids"]],
            "enrichment_state": _enrichment_state(
                scores,
                requested=int(enrichment["requested"]),
                completed=int(enrichment["completed"]),
                configured_top_n=enrich_top_n,
            ),
            "errors": errors,
        }
        self.db.commit()
        self.db.refresh(run)
        return run

    def _keyword_specs(self, payload: DiscoveryRunCreate) -> list[KeywordSpec]:
        specs: list[KeywordSpec] = []
        if payload.seed_list_id:
            seed_list = self.get_seed_list(payload.seed_list_id)
            if seed_list is None:
                raise ValueError(f"Seed list not found: {payload.seed_list_id}")
            for keyword in seed_list.keywords:
                if keyword.status == "active":
                    specs.append(
                        KeywordSpec(
                            keyword=keyword.keyword,
                            category=keyword.category,
                            seed_keyword_id=keyword.id,
                        )
                    )
        for input_keyword in payload.keywords:
            specs.append(
                KeywordSpec(
                    keyword=_clean(input_keyword.keyword),
                    category=_clean(input_keyword.category) if input_keyword.category else None,
                )
            )
        deduped: dict[tuple[str, str | None], KeywordSpec] = {}
        for spec in specs:
            deduped[(spec.keyword, spec.category)] = spec
        if not deduped:
            raise ValueError("Discovery run requires a seed list or at least one keyword.")
        return list(deduped.values())

    def _cluster_observations(
        self,
        keyword: KeywordSpec,
        observations: list[RawObservation],
    ) -> dict[_ClusterKey, list[RawObservation]]:
        clusters: dict[_ClusterKey, list[RawObservation]] = defaultdict(list)
        for observation in observations:
            key = _cluster_key(keyword.keyword, observation)
            clusters[key].append(observation)
        return clusters

    def _observations_for_run_or_keyword(
        self,
        *,
        plugin_run_id: uuid.UUID,
        source_plugin: str,
        keyword: str,
    ) -> list[RawObservation]:
        observations = list(
            self.db.scalars(
                select(RawObservation)
                .where(RawObservation.plugin_run_id == plugin_run_id)
                .order_by(RawObservation.created_at.asc())
            )
        )
        if observations:
            return observations

        existing = list(
            self.db.scalars(
                select(RawObservation)
                .where(RawObservation.source_plugin == source_plugin)
                .order_by(RawObservation.created_at.asc())
            )
        )
        return [
            observation
            for observation in existing
            if _clean((observation.metadata_ or {}).get("product_name")) == keyword
            or _clean((observation.metadata_ or {}).get("source_query")) == keyword
        ]

    def _match_or_create_product(
        self,
        label: str,
        observations: list[RawObservation],
    ) -> tuple[ProductCandidate, bool]:
        alias = normalize_alias(label)
        product = self.db.scalar(
            select(ProductCandidate)
            .join(ProductAlias)
            .where(ProductAlias.alias == alias)
            .limit(1)
        )
        if product is None:
            product = self.db.scalar(
                select(ProductCandidate)
                .where(func.lower(ProductCandidate.canonical_name) == label.lower())
                .limit(1)
            )
        if product is None:
            candidates = list(self.db.scalars(select(ProductCandidate)))
            for candidate in candidates:
                if SequenceMatcher(
                    None,
                    normalize_alias(candidate.canonical_name),
                    alias,
                ).ratio() >= 0.9:
                    product = candidate
                    break
        created = False
        if product is None:
            product = ProductCandidate(
                canonical_name=label,
                category=_most_common_metadata(observations, "amazon_category", "category"),
                description=observations[0].title if observations else None,
                status=ProductStatus.CANDIDATE,
            )
            self.db.add(product)
            self.db.flush()
            created = True
        if not self.db.scalar(
            select(ProductAlias.id)
            .where(ProductAlias.product_id == product.id, ProductAlias.alias == alias)
            .limit(1)
        ):
            self.db.add(
                ProductAlias(
                    product_id=product.id,
                    alias=alias,
                    source="discovery_run",
                    confidence=0.95,
                )
            )
        return product, created

    def _create_origin(
        self,
        run: DiscoveryRun,
        keyword: KeywordSpec,
        cluster: CandidateCluster,
        product: ProductCandidate,
        observation: RawObservation,
    ) -> bool:
        exists = self.db.scalar(
            select(CandidateOrigin.id)
            .where(
                CandidateOrigin.discovery_run_id == run.id,
                CandidateOrigin.seed_keyword_id == keyword.seed_keyword_id,
                CandidateOrigin.product_id == product.id,
                CandidateOrigin.source_plugin == observation.source_plugin,
                CandidateOrigin.source_external_id == observation.external_id,
            )
            .limit(1)
        )
        if exists:
            return False
        self.db.add(
            CandidateOrigin(
                product_id=product.id,
                discovery_run_id=run.id,
                seed_keyword_id=keyword.seed_keyword_id,
                candidate_cluster_id=cluster.id,
                source_plugin=observation.source_plugin,
                source_query=keyword.keyword,
                source_observation_id=observation.id,
                source_external_id=observation.external_id,
                title=observation.title,
                metadata_={
                    "source": observation.source,
                    "category": (observation.metadata_ or {}).get("amazon_category")
                    or (observation.metadata_ or {}).get("category"),
                    "asin": (observation.metadata_ or {}).get("asin"),
                },
            )
        )
        return True

    def _sync_and_score(self, product_ids: set[uuid.UUID]) -> dict[uuid.UUID, OpportunityScore | None]:
        comparable_service = ComparableService(self.db)
        scoring_service = ScoringService(self.db)
        scores: dict[uuid.UUID, OpportunityScore | None] = {}
        for product_id in product_ids:
            comparable_service.sync_product(product_id, create_snapshots=False)
            scores[product_id] = scoring_service.score_product(product_id)
        return scores

    def _latest_scores(self, product_ids: set[uuid.UUID]) -> dict[uuid.UUID, OpportunityScore | None]:
        rows = list(
            self.db.scalars(
                select(OpportunityScore)
                .where(OpportunityScore.product_id.in_(product_ids))
                .order_by(OpportunityScore.product_id, OpportunityScore.created_at.desc())
            )
        )
        latest: dict[uuid.UUID, OpportunityScore | None] = {product_id: None for product_id in product_ids}
        for row in rows:
            latest.setdefault(row.product_id, row)
            if latest[row.product_id] is None:
                latest[row.product_id] = row
        return latest

    def _enrich_top_n(
        self,
        payload: DiscoveryRunCreate,
        plugin_overrides: list[IngestionPlugin] | None,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None,
    ) -> int:
        if payload.enrich_top_n is not None:
            return max(0, min(int(payload.enrich_top_n), 100))
        if plugin_overrides is not None and refresh_pipeline_factory is None:
            return 0
        return max(0, min(int(self.settings.discovery_enrich_top_n), 100))

    def _enrichment_candidates(
        self,
        *,
        run: DiscoveryRun,
        scores: dict[uuid.UUID, OpportunityScore | None],
        limit: int,
        min_cluster_confidence: float,
    ) -> list[uuid.UUID]:
        if limit <= 0:
            return []
        rows: list[tuple[uuid.UUID, float, float, datetime]] = []
        clusters = list(
            self.db.scalars(
                select(CandidateCluster).where(CandidateCluster.discovery_run_id == run.id)
            )
        )
        for cluster in clusters:
            confidence = float((cluster.metadata_ or {}).get("cluster_confidence") or 0)
            if confidence < min_cluster_confidence:
                continue
            product_id = self.db.scalar(
                select(CandidateOrigin.product_id)
                .where(CandidateOrigin.candidate_cluster_id == cluster.id)
                .limit(1)
            )
            if product_id is None:
                continue
            score = scores.get(product_id)
            rows.append(
                (
                    product_id,
                    float(score.final_score if score else 0),
                    confidence,
                    cluster.created_at,
                )
            )
        selected: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        rows.sort(key=lambda row: (row[1], row[2], row[3]), reverse=True)
        for product_id, _score, _confidence, _created_at in rows:
            if product_id in seen:
                continue
            selected.append(product_id)
            seen.add(product_id)
            if len(selected) >= limit:
                break
        return selected

    def _enrich_products(
        self,
        product_ids: list[uuid.UUID],
        *,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None,
    ) -> dict:
        if not product_ids:
            return {
                "requested": 0,
                "completed": 0,
                "failed": 0,
                "observations_created": 0,
                "errors": [],
                "product_ids": [],
            }
        factory = refresh_pipeline_factory or AmazonRefreshPipeline
        refresh = factory(self.db)
        completed = 0
        failed = 0
        observations_created = 0
        errors: list[str] = []
        enriched: list[uuid.UUID] = []
        for product_id in product_ids:
            response: PipelineRunResponse = refresh.run_product(product_id)
            observations_created += response.observations_created
            if response.status == "failed":
                failed += 1
            else:
                completed += 1
                enriched.append(product_id)
            errors.extend(response.errors)
        return {
            "requested": len(product_ids),
            "completed": completed,
            "failed": failed,
            "observations_created": observations_created,
            "errors": errors,
            "product_ids": enriched,
        }

    def _create_results(
        self,
        run: DiscoveryRun,
        scores: dict[uuid.UUID, OpportunityScore | None],
    ) -> int:
        clusters = list(
            self.db.scalars(
                select(CandidateCluster).where(CandidateCluster.discovery_run_id == run.id)
            )
        )
        created = 0
        result_rows: list[DiscoveryRunResult] = []
        for cluster in clusters:
            product_id = self.db.scalar(
                select(CandidateOrigin.product_id)
                .where(CandidateOrigin.candidate_cluster_id == cluster.id)
                .limit(1)
            )
            if product_id is None:
                continue
            score = scores.get(product_id)
            result = DiscoveryRunResult(
                discovery_run_id=run.id,
                seed_keyword_id=cluster.seed_keyword_id,
                candidate_cluster_id=cluster.id,
                product_id=product_id,
                score_snapshot_id=score.id if score else None,
                status="created",
                opportunity_score=score.final_score if score else None,
                recommendation=score.recommendation.value if score else None,
                metadata_={
                    "cluster_label": cluster.label,
                    "source_query": cluster.source_query,
                },
            )
            self.db.add(result)
            result_rows.append(result)
            created += 1
        self.db.flush()
        result_rows.sort(key=lambda row: row.opportunity_score or -1, reverse=True)
        for index, row in enumerate(result_rows, start=1):
            row.rank_position = index
        self.db.commit()
        return created


@dataclass(frozen=True)
class _ClusterKey:
    label: str
    normalized_key: str
    representative_title: str | None = field(compare=False)
    method: str = field(compare=False)


def _cluster_key(seed_query: str, observation: RawObservation) -> _ClusterKey:
    metadata = observation.metadata_ or {}
    product_type = str(metadata.get("amazon_product_type") or metadata.get("product_type") or "").strip()
    if product_type and normalize_alias(product_type) not in GENERIC_PRODUCT_TYPES:
        label = _label_from_tokens(product_type.replace("_", " ").split(), fallback=observation.title)
        return _ClusterKey(
            label=label,
            normalized_key=normalize_alias(label),
            representative_title=observation.title,
            method="amazon_product_type",
        )

    title = observation.title or metadata.get("title") or metadata.get("product_name") or seed_query
    title_tokens = _concept_tokens(str(title))
    if len(title_tokens) < 2:
        title_tokens = _concept_tokens(seed_query)
    seed_tokens = set(_concept_tokens(seed_query))
    if seed_tokens and set(title_tokens).issubset(seed_tokens):
        title_tokens = _concept_tokens(str(title))
    label = _label_from_tokens(title_tokens[:3], fallback=str(title))
    return _ClusterKey(
        label=label,
        normalized_key=normalize_alias(label),
        representative_title=str(title),
        method="title_tokens",
    )


def _concept_tokens(value: str) -> list[str]:
    normalized = normalize_alias(re.sub(r"[^a-zA-Z0-9 ]+", " ", value))
    return [
        token
        for token in normalized.split()
        if token and token not in CONCEPT_STOP_WORDS and not token.isdigit()
    ]


def _label_from_tokens(tokens: list[str], *, fallback: str | None) -> str:
    if tokens:
        return " ".join(tokens).lower()[:255]
    return _clean(fallback or "unknown product")


def _cluster_confidence(cluster_key: _ClusterKey, observations: list[RawObservation]) -> float:
    if not observations:
        return 0.0
    base = 0.72 if cluster_key.method == "amazon_product_type" else 0.62
    observation_bonus = min(max(len(observations) - 1, 0), 4) * 0.05
    label_penalty = 0.2 if cluster_key.normalized_key in {"unknown", "unknown product"} else 0.0
    return round(max(0.0, min(0.95, base + observation_bonus - label_penalty)), 2)


def _most_common_metadata(observations: list[RawObservation], *keys: str) -> str | None:
    values: list[str] = []
    for observation in observations:
        metadata = observation.metadata_ or {}
        for key in keys:
            value = metadata.get(key)
            if value:
                values.append(str(value).lower())
                break
    if not values:
        return None
    return Counter(values).most_common(1)[0][0][:120]


def _clean(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())[:255]


def _status(
    *,
    keyword_count: int,
    keyword_successes: int,
    errors: list[str],
    results_created: int,
) -> str:
    if results_created == 0:
        return "failed" if errors else "success"
    if errors or keyword_successes < keyword_count:
        return "partial_success"
    return "success"


def _enrichment_state(
    scores: dict[uuid.UUID, OpportunityScore | None],
    *,
    requested: int,
    completed: int,
    configured_top_n: int,
) -> str:
    if not scores:
        return "no_candidates"
    if configured_top_n <= 0:
        return "preliminary_scored"
    if requested == 0:
        return "no_enrichment_candidates"
    if completed == requested:
        return "enriched"
    if completed > 0:
        return "partially_enriched"
    return "enrichment_failed"
