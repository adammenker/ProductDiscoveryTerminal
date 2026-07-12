from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.schemas.discovery import DiscoveryKeywordInput, DiscoveryRunCreate
from app.services import discovery_worker
from app.services.discovery_service import DiscoveryService


def test_recovery_requeues_unfinished_discovery_runs(
    db_session: Session,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    service = DiscoveryService(db_session)
    queued = service.enqueue_discovery(
        DiscoveryRunCreate(keywords=[DiscoveryKeywordInput(keyword="queued product")])
    )
    running = service.enqueue_discovery(
        DiscoveryRunCreate(keywords=[DiscoveryKeywordInput(keyword="running product")])
    )
    running.status = "running"
    running.summary = {**running.summary, "progress_stage": "enrichment"}
    db_session.commit()

    @contextmanager
    def session_factory():
        yield db_session

    submitted: list[str] = []

    def submit(run_id: str) -> bool:
        submitted.append(run_id)
        return True

    monkeypatch.setattr(discovery_worker, "SessionLocal", session_factory)
    monkeypatch.setattr(discovery_worker, "queue_discovery_run", submit)

    recovered = discovery_worker.recover_discovery_runs()

    db_session.refresh(running)
    assert recovered == 2
    assert submitted == [str(queued.id), str(running.id)]
    assert running.status == "queued"
    assert running.summary["progress_stage"] == "queued"
    assert running.summary["recovery_count"] == 1
