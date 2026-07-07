from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ObservationEntityType, PluginRun, PluginType, RawObservation, RunStatus
from app.models.product import ProductCandidate
from app.services.normalization_service import NormalizationService, normalize_alias


def test_alias_normalization_removes_noise() -> None:
    assert normalize_alias("Best Facial Ice Rollers - Pack") == "facial ice roller"


def test_normalization_links_repeated_aliases_in_same_batch(db_session: Session) -> None:
    run = PluginRun(
        plugin_name="test",
        plugin_type=PluginType.INGESTION,
        status=RunStatus.SUCCESS,
        started_at=datetime.now(UTC),
        records_created=2,
        parameters={},
    )
    db_session.add(run)
    db_session.commit()

    for index, source in enumerate(["source_a", "source_b"]):
        db_session.add(
            RawObservation(
                plugin_run_id=run.id,
                source=source,
                source_plugin="test",
                observed_at=datetime.now(UTC),
                entity_type=ObservationEntityType.PRODUCT,
                title="Facial Ice Roller - marketplace result",
                raw_text="A simple skincare tool.",
                metrics={},
                metadata_={"product_name": "facial ice roller", "category": "beauty"},
                media_urls=[],
                content_hash=f"hash-{index}",
            )
        )
    db_session.commit()

    products = NormalizationService(db_session).normalize_new_observations()

    assert len(products) == 1
    product_count = db_session.scalar(select(func.count()).select_from(ProductCandidate))
    assert product_count == 1
    linked = db_session.scalars(select(RawObservation)).all()
    assert {observation.product_id for observation in linked} == {products[0].id}
