from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import PluginRun
from app.plugins.registry import list_plugins
from app.schemas.plugin import PluginCatalog, PluginRunSummary

router = APIRouter(tags=["plugins"])


@router.get("/plugins", response_model=PluginCatalog)
def plugins() -> dict:
    return list_plugins()


@router.get("/plugin-runs", response_model=list[PluginRunSummary])
def plugin_runs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[PluginRunSummary]:
    runs = db.scalars(
        select(PluginRun)
        .order_by(PluginRun.started_at.desc(), PluginRun.created_at.desc())
        .limit(limit)
    ).all()
    return [
        PluginRunSummary(
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
        for run in runs
    ]

