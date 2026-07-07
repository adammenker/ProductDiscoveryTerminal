from __future__ import annotations

from sqlalchemy.orm import Session

from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import IngestionQuery, PipelineRunRequest


def test_pipeline_happy_path_and_observation_deduplication(db_session: Session) -> None:
    runner = PipelineRunner(db_session)

    first = runner.run(PipelineRunRequest())
    second = runner.run(PipelineRunRequest())

    assert first.status == "success"
    assert first.observations_created == 22
    assert first.products_updated == 7
    assert first.scores_updated == 7
    assert second.status == "success"
    assert second.observations_created == 0
    assert second.products_updated == 0
    assert second.scores_updated == 0
    assert "etsy_api" not in {run.plugin_name for run in first.plugin_runs}
    assert "alibaba_open_api" not in {run.plugin_name for run in first.plugin_runs}


def test_pipeline_captures_plugin_failure(db_session: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class BrokenPlugin:
        name = "broken_mock"
        version = "0.1.0"
        manifest = {"name": name, "type": "ingestion", "description": "Broken plugin"}

        def fetch(self, query: IngestionQuery):  # type: ignore[no-untyped-def]
            raise RuntimeError("boom")

    monkeypatch.setattr("app.pipeline.runner.get_ingestion_plugins", lambda names=None: [BrokenPlugin()])

    result = PipelineRunner(db_session).run(PipelineRunRequest(plugins=["broken_mock"]))

    assert result.status == "failed"
    assert result.plugin_runs[0].status == "failed"
    assert "boom" in result.errors[0]
