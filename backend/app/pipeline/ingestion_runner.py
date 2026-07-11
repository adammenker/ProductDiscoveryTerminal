from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ObservationEntityType, PluginRun, PluginType, RawObservation, RunStatus
from app.schemas.plugin import IngestionPlugin, IngestionQuery
from app.services.observation_service import observation_content_hash

logger = logging.getLogger(__name__)


class IngestionRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_plugin(self, plugin: IngestionPlugin, query: IngestionQuery) -> PluginRun:
        run = PluginRun(
            plugin_name=plugin.name,
            plugin_type=PluginType.INGESTION,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
            parameters=query.model_dump(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        logger.info("Starting ingestion plugin %s", plugin.name)
        try:
            observations = plugin.fetch(query)
            request_errors = _request_errors(observations)
            created = 0
            skipped = 0
            for dto in observations:
                dto.metadata = {
                    **dto.metadata,
                    **({"source_query": query.query} if query.query and "source_query" not in dto.metadata else {}),
                    **({"source_category": query.category} if query.category and "source_category" not in dto.metadata else {}),
                }
                dto.metadata.pop("request_errors", None)
                content_hash = observation_content_hash(dto)
                exists = self.db.scalar(
                    select(RawObservation.id)
                    .where(RawObservation.content_hash == content_hash)
                    .limit(1)
                )
                if exists is not None:
                    skipped += 1
                    continue
                self.db.add(
                    RawObservation(
                        plugin_run_id=run.id,
                        source=dto.source,
                        source_plugin=dto.source_plugin,
                        observed_at=dto.observed_at,
                        entity_type=ObservationEntityType(dto.entity_type),
                        external_id=dto.external_id,
                        title=dto.title,
                        url=dto.url,
                        raw_text=dto.raw_text,
                        metrics=dto.metrics,
                        metadata_=dto.metadata,
                        media_urls=dto.media_urls,
                        content_hash=content_hash,
                    )
                )
                created += 1

            run.status = RunStatus.PARTIAL_SUCCESS if request_errors else RunStatus.SUCCESS
            run.records_created = created
            run.records_updated = skipped
            if request_errors:
                run.error_message = "; ".join(
                    f"{item['asin']}: {item['error']}" for item in request_errors
                )[:2000]
            run.finished_at = datetime.now(UTC)
            self.db.commit()
            logger.info("Finished ingestion plugin %s: %s created, %s skipped", plugin.name, created, skipped)
        except Exception as exc:  # noqa: BLE001
            self.db.rollback()
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = datetime.now(UTC)
            self.db.add(run)
            self.db.commit()
            logger.exception("Ingestion plugin %s failed", plugin.name)
        self.db.refresh(run)
        return run


def _request_errors(observations: list) -> list[dict[str, str]]:  # type: ignore[type-arg]
    errors: dict[tuple[str, str], dict[str, str]] = {}
    for observation in observations:
        for item in observation.metadata.get("request_errors") or []:
            if not isinstance(item, dict):
                continue
            asin = str(item.get("asin") or "unknown")
            error = str(item.get("error") or "request failed")
            errors[(asin, error)] = {"asin": asin, "error": error}
    return list(errors.values())
