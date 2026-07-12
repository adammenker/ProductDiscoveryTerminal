from __future__ import annotations

import re
import time
import uuid
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

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
OPPORTUNITY_VARIANT_TERMS = {
    "black", "blue", "compact", "deluxe", "foldable", "gray", "green", "grey",
    "large", "mini", "pink", "portable", "premium", "professional", "red",
    "small", "stainless", "steel", "white", "xl",
}
OPPORTUNITY_ACCESSORY_TERMS = {
    "adapter", "bag", "case", "cover", "holder", "liner", "rack", "replacement",
    "shelf", "stand",
}


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
        return list(
            self.db.scalars(
                select(SeedList)
                .options(selectinload(SeedList.keywords))
                .order_by(SeedList.created_at.desc())
            )
        )

    def list_runs(self, limit: int = 25, *, include_details: bool = False) -> list[DiscoveryRun]:
        statement = (
            select(DiscoveryRun)
            .order_by(DiscoveryRun.started_at.desc())
            .limit(max(1, min(limit, 100)))
        )
        if include_details:
            statement = statement.options(
                selectinload(DiscoveryRun.clusters),
                selectinload(DiscoveryRun.results),
                selectinload(DiscoveryRun.origins),
            )
        return list(
            self.db.scalars(statement)
        )

    def get_seed_list(self, seed_list_id: uuid.UUID | str) -> SeedList | None:
        return self.db.get(SeedList, uuid.UUID(str(seed_list_id)))

    def get_run(self, run_id: uuid.UUID | str) -> DiscoveryRun | None:
        return self.db.scalar(
            select(DiscoveryRun)
            .where(DiscoveryRun.id == uuid.UUID(str(run_id)))
            .options(
                selectinload(DiscoveryRun.clusters),
                selectinload(DiscoveryRun.results),
                selectinload(DiscoveryRun.origins),
            )
        )

    def run_discovery(
        self,
        payload: DiscoveryRunCreate,
        *,
        plugin_overrides: list[IngestionPlugin] | None = None,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None = None,
    ) -> DiscoveryRun:
        plugin_names = payload.plugins or DEFAULT_DISCOVERY_PLUGINS
        self._keyword_specs(payload)
        run = DiscoveryRun(
            seed_list_id=uuid.UUID(payload.seed_list_id) if payload.seed_list_id else None,
            status="running",
            started_at=datetime.now(UTC),
            source_plugins=plugin_names,
            parameters=payload.model_dump(),
            summary=self._progress_summary(
                stage="starting",
                percent=0,
                message="Discovery run starting",
            ),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return self._process_run(
            run,
            payload,
            plugin_overrides=plugin_overrides,
            refresh_pipeline_factory=refresh_pipeline_factory,
        )

    def enqueue_discovery(self, payload: DiscoveryRunCreate) -> DiscoveryRun:
        keywords = self._keyword_specs(payload)
        plugin_names = payload.plugins or DEFAULT_DISCOVERY_PLUGINS
        run = DiscoveryRun(
            seed_list_id=uuid.UUID(payload.seed_list_id) if payload.seed_list_id else None,
            status="queued",
            started_at=datetime.now(UTC),
            source_plugins=plugin_names,
            parameters=payload.model_dump(),
            summary=self._progress_summary(
                stage="queued",
                percent=0,
                message="Discovery run queued",
                extra={
                    "keywords_requested": len(keywords),
                    "plugins_requested": plugin_names,
                    "enrichment_state": "queued",
                },
            ),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def process_queued_run(
        self,
        run_id: uuid.UUID | str,
        *,
        plugin_overrides: list[IngestionPlugin] | None = None,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None = None,
    ) -> DiscoveryRun:
        normalized_run_id = uuid.UUID(str(run_id))
        run = self.db.scalar(
            select(DiscoveryRun)
            .where(DiscoveryRun.id == normalized_run_id)
            .with_for_update()
        )
        if run is None:
            raise ValueError(f"Discovery run not found: {run_id}")
        if run.status != "queued":
            self.db.rollback()
            return run
        run.status = "running"
        run.summary = self._progress_summary(
            stage="starting",
            percent=max(1, int((run.summary or {}).get("progress_percent") or 0)),
            message="Discovery worker claimed queued run",
            extra=run.summary or {},
        )
        self.db.commit()
        self.db.refresh(run)
        payload = DiscoveryRunCreate.model_validate(run.parameters)
        return self._process_run(
            run,
            payload,
            plugin_overrides=plugin_overrides,
            refresh_pipeline_factory=refresh_pipeline_factory,
        )

    def _process_run(
        self,
        run: DiscoveryRun,
        payload: DiscoveryRunCreate,
        *,
        plugin_overrides: list[IngestionPlugin] | None = None,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None = None,
    ) -> DiscoveryRun:
        run_id = run.id
        try:
            return self._process_run_unchecked(
                run,
                payload,
                plugin_overrides=plugin_overrides,
                refresh_pipeline_factory=refresh_pipeline_factory,
            )
        except Exception as exc:
            self.db.rollback()
            failed_run = self.db.get(DiscoveryRun, run_id)
            if failed_run is None:
                raise
            failed_run.status = "failed"
            failed_run.finished_at = datetime.now(UTC)
            failed_run.error_message = str(exc)[:2000]
            failed_run.summary = self._progress_summary(
                stage="failed",
                percent=100,
                message="Discovery run failed",
                extra={
                    **(failed_run.summary or {}),
                    "errors": [str(exc)],
                    "enrichment_state": "failed",
                },
            )
            self.db.commit()
            self.db.refresh(failed_run)
            raise

    def _process_run_unchecked(
        self,
        run: DiscoveryRun,
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
        run.status = "running"
        run.source_plugins = [plugin.name for plugin in plugins]
        self._set_run_progress(
            run,
            stage="catalog_scan",
            percent=5,
            message="Running bounded catalog searches",
            extra={
                "keywords_requested": len(keywords),
                "plugins_requested": plugin_names,
                "plugins_run": [plugin.name for plugin in plugins],
                "enrichment_state": "catalog_scan",
                "worker_started_at": datetime.now(UTC).isoformat(),
            },
        )
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
        for keyword_index, keyword in enumerate(keywords, start=1):
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
            self._set_run_progress(
                run,
                stage="catalog_scan",
                percent=_bounded_percent(
                    completed=keyword_index,
                    total=len(keywords),
                    start=5,
                    end=45,
                ),
                message="Running bounded catalog searches",
                extra={
                    "keywords_requested": len(keywords),
                    "keywords_succeeded": keyword_successes,
                    "observations_created": observations_created,
                    "clusters_created": clusters_created,
                    "origins_created": origins_created,
                    "products_matched_or_created": len(product_ids),
                },
            )

        self._set_run_progress(
            run,
            stage="preliminary_scoring",
            percent=55,
            message="Scoring discovered candidates before enrichment",
            extra={
                "candidates_created": candidates_created,
                "candidates_matched": candidates_matched,
                "products_matched_or_created": len(product_ids),
            },
        )
        preliminary_scores = self._sync_and_score(product_ids)
        enrichment_candidates = self._enrichment_candidates(
            run=run,
            scores=preliminary_scores,
            limit=enrich_top_n,
            min_cluster_confidence=min_cluster_confidence,
        )
        self._set_run_progress(
            run,
            stage="enrichment",
            percent=65,
            message="Refreshing pricing and fee evidence for top candidates",
            extra={
                "enrichment_top_n": enrich_top_n,
                "min_cluster_confidence": min_cluster_confidence,
                "enrichment_candidates": len(enrichment_candidates),
                "enrichment_requested": len(enrichment_candidates),
                "enriched_candidates": 0,
                "enrichment_failed": 0,
                "enrichment_state": "enrichment",
            },
        )

        def enrichment_progress(completed: int, total: int, product_id: uuid.UUID) -> None:
            self._set_run_progress(
                run,
                stage="enrichment",
                percent=_bounded_percent(completed=completed, total=total, start=65, end=88),
                message="Refreshing pricing and fee evidence for top candidates",
                extra={
                    "enrichment_requested": total,
                    "enriched_candidates": completed,
                    "latest_enriched_product_id": str(product_id),
                },
            )

        enrichment = self._enrich_products(
            enrichment_candidates,
            refresh_pipeline_factory=refresh_pipeline_factory,
            progress_callback=enrichment_progress,
        )
        errors.extend(enrichment["errors"])
        self._set_run_progress(
            run,
            stage="final_ranking",
            percent=92,
            message="Re-scoring and ranking discovery results",
            extra={
                "enriched_candidates": enrichment["completed"],
                "enrichment_failed": enrichment["failed"],
                "enrichment_observations_created": enrichment["observations_created"],
            },
        )
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
        summary = dict(run.summary or {})
        summary.update({
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
            "enrichment_max_per_source_query": int(
                self.settings.discovery_enrich_max_per_source_query
            ),
            "enrichment_max_per_opportunity": int(
                self.settings.discovery_enrich_max_per_opportunity
            ),
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
            "progress_stage": "completed",
            "progress_percent": 100,
            "progress_message": "Discovery run complete",
            "last_progress_at": datetime.now(UTC).isoformat(),
        })
        run.summary = summary
        self.db.commit()
        self.db.refresh(run)
        return run

    def _set_run_progress(
        self,
        run: DiscoveryRun,
        *,
        stage: str,
        percent: int,
        message: str,
        extra: dict | None = None,
    ) -> None:
        summary = self._progress_summary(
            stage=stage,
            percent=percent,
            message=message,
            extra={
                **(run.summary or {}),
                **(extra or {}),
            },
        )
        run.summary = summary
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

    def _progress_summary(
        self,
        *,
        stage: str,
        percent: int,
        message: str,
        extra: dict | None = None,
    ) -> dict:
        return {
            **(extra or {}),
            "progress_stage": stage,
            "progress_percent": max(0, min(int(percent), 100)),
            "progress_message": message,
            "last_progress_at": datetime.now(UTC).isoformat(),
        }

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
        rows: list[tuple[uuid.UUID, float, float, datetime, str, str]] = []
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
            score_breakdown = score.score_breakdown if score else {}
            research_priority = score_breakdown.get("ranking_priority_score")
            _group_label, group_key = _opportunity_group(cluster.label, cluster.source_query)
            rows.append(
                (
                    product_id,
                    float(
                        research_priority
                        if research_priority is not None
                        else score.final_score if score else 0
                    ),
                    confidence,
                    cluster.created_at,
                    normalize_alias(cluster.source_query) or "unknown-query",
                    group_key,
                )
            )
        selected: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        selected_groups: Counter[str] = Counter()
        max_per_query = max(1, int(self.settings.discovery_enrich_max_per_source_query))
        max_per_group = max(1, int(self.settings.discovery_enrich_max_per_opportunity))
        query_buckets: dict[str, list[tuple[uuid.UUID, float, float, datetime, str, str]]] = (
            defaultdict(list)
        )
        for row in rows:
            query_buckets[row[4]].append(row)
        for bucket in query_buckets.values():
            bucket.sort(key=lambda row: (row[1], row[2], row[3]), reverse=True)

        # Round-robin across seed queries so a strong niche cannot consume the
        # entire top-N budget. Within each query, prefer distinct opportunities.
        query_order = sorted(
            query_buckets,
            key=lambda key: max((row[1], row[2]) for row in query_buckets[key]),
            reverse=True,
        )
        query_counts: Counter[str] = Counter()
        while len(selected) < limit:
            made_progress = False
            for query_key in query_order:
                if query_counts[query_key] >= max_per_query:
                    continue
                bucket = query_buckets[query_key]
                candidate_index = next(
                    (
                        index
                        for index, row in enumerate(bucket)
                        if row[0] not in seen and selected_groups[row[5]] < max_per_group
                    ),
                    None,
                )
                if candidate_index is None:
                    continue
                product_id, _score, _confidence, _created_at, _query, group_key = bucket.pop(
                    candidate_index
                )
                selected.append(product_id)
                seen.add(product_id)
                selected_groups[group_key] += 1
                query_counts[query_key] += 1
                made_progress = True
                if len(selected) >= limit:
                    break
            if not made_progress:
                break
        return selected

    def _enrich_products(
        self,
        product_ids: list[uuid.UUID],
        *,
        refresh_pipeline_factory: Callable[[Session], AmazonRefreshPipeline] | None,
        progress_callback: Callable[[int, int, uuid.UUID], None] | None = None,
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
        throttle_seconds = max(0.0, float(self.settings.discovery_enrichment_request_interval_seconds))
        for index, product_id in enumerate(product_ids, start=1):
            if index > 1 and refresh_pipeline_factory is None and throttle_seconds > 0:
                time.sleep(throttle_seconds)
            response: PipelineRunResponse = refresh.run_product(product_id)
            observations_created += response.observations_created
            if response.status == "failed":
                failed += 1
            else:
                completed += 1
                enriched.append(product_id)
            errors.extend(response.errors)
            if progress_callback is not None:
                progress_callback(index, len(product_ids), product_id)
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
            score_breakdown = score.score_breakdown if score else {}
            data_readiness = score_breakdown.get("data_readiness") or {}
            result = DiscoveryRunResult(
                discovery_run_id=run.id,
                seed_keyword_id=cluster.seed_keyword_id,
                candidate_cluster_id=cluster.id,
                product_id=product_id,
                score_snapshot_id=score.id if score else None,
                status="created",
                opportunity_score=score.final_score if score else None,
                evidence_confidence_score=(
                    float(score_breakdown.get("evidence_confidence_score") or 0)
                    if score
                    else None
                ),
                ranking_priority_score=(
                    float(score_breakdown["ranking_priority_score"])
                    if score and score_breakdown.get("ranking_priority_score") is not None
                    else None
                ),
                recommendation=score.recommendation.value if score else None,
                metadata_={
                    "cluster_label": cluster.label,
                    "source_query": cluster.source_query,
                    "data_readiness_state": data_readiness.get("state", "catalog_only"),
                    "raw_opportunity_score": score_breakdown.get("raw_opportunity_score"),
                    "ranking_priority": score_breakdown.get("ranking_priority") or {},
                },
            )
            self.db.add(result)
            result_rows.append(result)
            created += 1
        self.db.flush()
        grouped: dict[str, list[DiscoveryRunResult]] = defaultdict(list)
        for row in result_rows:
            metadata = row.metadata_ or {}
            group_label, group_key = _opportunity_group(
                str(metadata.get("cluster_label") or ""),
                str(metadata.get("source_query") or ""),
            )
            metadata.update(
                {
                    "opportunity_group_key": group_key,
                    "opportunity_group_label": group_label,
                }
            )
            row.metadata_ = metadata
            grouped[group_key].append(row)

        representatives: list[DiscoveryRunResult] = []
        for members in grouped.values():
            members.sort(key=lambda row: row.opportunity_score or -1, reverse=True)
            representatives.append(members[0])
            for group_rank, row in enumerate(members, start=1):
                metadata = dict(row.metadata_ or {})
                metadata.update(
                    {
                        "opportunity_group_rank": group_rank,
                        "opportunity_group_member_count": len(members),
                        "is_opportunity_representative": group_rank == 1,
                    }
                )
                row.metadata_ = metadata
                row.rank_position = None

        representatives.sort(key=lambda row: row.opportunity_score or -1, reverse=True)
        for index, row in enumerate(representatives, start=1):
            row.rank_position = index
        run.summary = {
            **(run.summary or {}),
            "opportunity_groups_created": len(grouped),
            "variants_collapsed": max(0, len(result_rows) - len(grouped)),
        }
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


def _opportunity_group(cluster_label: str, source_query: str) -> tuple[str, str]:
    """Roll brand/listing-level clusters into a stable product opportunity concept."""
    label_tokens = _opportunity_tokens(cluster_label)
    query_tokens = _opportunity_tokens(source_query)
    label_set = set(label_tokens)
    query_set = set(query_tokens)
    accessory_mismatch = bool(
        (label_set & OPPORTUNITY_ACCESSORY_TERMS) - (query_set & OPPORTUNITY_ACCESSORY_TERMS)
    )

    # Amazon commonly returns brand-prefixed variants for a focused query. Treat
    # heated/bucket towel listings as variants of the towel-warmer opportunity.
    towel_warmer_terms = {"bucket", "heater", "warmer"}
    if (
        {"towel", "warmer"}.issubset(query_set)
        and "towel" in label_set
        and not accessory_mismatch
    ):
        if label_set & towel_warmer_terms:
            return "towel warmer", "towel-warmer"

    # A short focused query is the best concept label when the listing label
    # contains all of its meaningful terms, usually after a brand prefix.
    query_coverage = len(query_set & label_set) / len(query_set) if query_set else 0
    if 1 < len(query_tokens) <= 4 and query_coverage >= 0.75 and not accessory_mismatch:
        label = " ".join(query_tokens)
        return label, normalize_alias(label)

    # Otherwise retain the catalog cluster. This prevents broad seeds such as
    # "travel organizer" from collapsing unrelated products into one result.
    label = " ".join(label_tokens) or _clean(cluster_label or source_query or "unknown product")
    return label, normalize_alias(label)


def _opportunity_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    normalized = normalize_alias(re.sub(r"[^a-zA-Z0-9 ]+", " ", value))
    retained_stop_words = OPPORTUNITY_ACCESSORY_TERMS | {"kit", "set"}
    raw_tokens = [
        token
        for token in normalized.split()
        if token and (token not in CONCEPT_STOP_WORDS or token in retained_stop_words)
    ]
    for token in raw_tokens:
        if token in OPPORTUNITY_VARIANT_TERMS or re.fullmatch(r"\d+(?:oz|in|inch|cm|mm|qt|pk)", token):
            continue
        canonical = {
            "heated": "warmer",
            "heating": "warmer",
            "warming": "warmer",
            "warmers": "warmer",
        }.get(token, token)
        if canonical.endswith("s") and len(canonical) > 4 and not canonical.endswith("ss"):
            canonical = canonical[:-1]
        tokens.append(canonical)
    return tokens


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
        return "failed" if errors or keyword_successes < keyword_count else "success"
    if errors or keyword_successes < keyword_count:
        return "partial_success"
    return "success"


def _bounded_percent(*, completed: int, total: int, start: int, end: int) -> int:
    if total <= 0:
        return end
    ratio = max(0.0, min(float(completed) / float(total), 1.0))
    return int(round(start + (end - start) * ratio))


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
