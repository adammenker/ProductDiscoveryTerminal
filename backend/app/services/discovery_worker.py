from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import DiscoveryRun
from app.services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="discovery-worker")
_lock = threading.Lock()
_in_flight: set[str] = set()


def queue_discovery_run(run_id: str) -> bool:
    with _lock:
        if run_id in _in_flight:
            return False
        _in_flight.add(run_id)
    future = _executor.submit(_process_discovery_run, run_id)
    future.add_done_callback(lambda completed: _release_run(run_id, completed))
    return True


def discovery_run_is_in_flight(run_id: str) -> bool:
    with _lock:
        return run_id in _in_flight


def recover_discovery_runs() -> int:
    """Requeue unfinished work after a backend process restart."""
    with SessionLocal() as db:
        runs = list(
            db.scalars(
                select(DiscoveryRun)
                .where(DiscoveryRun.status.in_({"queued", "running"}))
                .order_by(DiscoveryRun.started_at.asc())
            )
        )
        for run in runs:
            if run.status == "running":
                summary = dict(run.summary or {})
                summary.update(
                    {
                        "progress_stage": "queued",
                        "progress_message": "Recovered after backend restart",
                        "recovery_count": int(summary.get("recovery_count") or 0) + 1,
                    }
                )
                run.status = "queued"
                run.summary = summary
        db.commit()
        run_ids = [str(run.id) for run in runs]

    for run_id in run_ids:
        queue_discovery_run(run_id)
    if run_ids:
        logger.info("Recovered %s unfinished discovery run(s)", len(run_ids))
    return len(run_ids)


def _process_discovery_run(run_id: str) -> None:
    with SessionLocal() as db:
        DiscoveryService(db).process_queued_run(run_id)


def _release_run(run_id: str, future: Future[None]) -> None:
    with _lock:
        _in_flight.discard(run_id)
    exception = future.exception()
    if exception is not None:
        logger.error(
            "Discovery run %s failed in worker",
            run_id,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
