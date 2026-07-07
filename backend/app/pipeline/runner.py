from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import PluginRun, RunStatus
from app.pipeline.analyzer_runner import AnalyzerRunner
from app.pipeline.ingestion_runner import IngestionRunner
from app.plugins.registry import get_ingestion_plugins
from app.schemas.plugin import (
    IngestionQuery,
    PipelineRunRequest,
    PipelineRunResponse,
    PluginRunSummary,
)
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, request: PipelineRunRequest) -> PipelineRunResponse:
        logger.info("Starting product discovery pipeline")
        selected_plugins = get_ingestion_plugins(request.plugins)
        errors: list[str] = []
        if request.plugins:
            found = {plugin.name for plugin in selected_plugins}
            missing = sorted(set(request.plugins) - found)
            errors.extend([f"Unknown ingestion plugin: {name}" for name in missing])

        ingestion_runner = IngestionRunner(self.db)
        plugin_runs: list[PluginRun] = []
        observations_created = 0
        for plugin in selected_plugins:
            run = ingestion_runner.run_plugin(plugin, _limit_query(request.query))
            plugin_runs.append(run)
            observations_created += run.records_created

        updated_products = NormalizationService(self.db).normalize_new_observations()
        product_ids: list[UUID | str] = [str(product.id) for product in updated_products]

        if request.run_analyzers and product_ids:
            analyzer_runs = AnalyzerRunner(self.db).run(product_ids)
            plugin_runs.extend(analyzer_runs)

        scores_updated = 0
        if request.score and product_ids:
            scores = ScoringService(self.db).score_products(product_ids)
            scores_updated = len(scores)

        status = _pipeline_status(plugin_runs, errors)
        logger.info(
            "Finished product discovery pipeline: %s products, %s scores, status=%s",
            len(product_ids),
            scores_updated,
            status,
        )
        return PipelineRunResponse(
            status=status,
            plugin_runs=[_run_summary(run) for run in plugin_runs],
            products_updated=len(product_ids),
            scores_updated=scores_updated,
            observations_created=observations_created,
            errors=errors + _run_errors(plugin_runs),
        )


def _limit_query(query: IngestionQuery) -> IngestionQuery:
    return IngestionQuery(
        query=query.query,
        category=query.category,
        limit=max(1, min(query.limit, 1000)),
        metadata=query.metadata,
    )


def _pipeline_status(plugin_runs: list[PluginRun], errors: list[str]) -> str:
    if errors and not plugin_runs:
        return RunStatus.FAILED.value
    statuses = [run.status for run in plugin_runs]
    if any(status in {RunStatus.FAILED, RunStatus.PARTIAL_SUCCESS} for status in statuses) or errors:
        if any(status == RunStatus.SUCCESS for status in statuses):
            return RunStatus.PARTIAL_SUCCESS.value
        return RunStatus.FAILED.value
    return RunStatus.SUCCESS.value


def _run_errors(plugin_runs: list[PluginRun]) -> list[str]:
    return [
        f"{run.plugin_name}: {run.error_message}"
        for run in plugin_runs
        if run.error_message
    ]


def _run_summary(run: PluginRun) -> PluginRunSummary:
    return PluginRunSummary(
        id=str(run.id),
        plugin_name=run.plugin_name,
        plugin_type=run.plugin_type.value,
        status=run.status.value,
        records_created=run.records_created,
        records_updated=run.records_updated,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
