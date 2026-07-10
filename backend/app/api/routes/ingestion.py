from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import PipelineRunRequest, PipelineRunResponse

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=PipelineRunResponse)
def run_ingestion(
    request: PipelineRunRequest | None = None,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    return PipelineRunner(db).run(request or PipelineRunRequest())


@router.post("/refresh-existing", response_model=PipelineRunResponse)
def refresh_existing_products(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    return AmazonRefreshPipeline(db).run(limit=limit)
