from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ProductCandidate, ProductStatus
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import (
    PipelineRunRequest,
    PipelineRunResponse,
    ProductResearchRequest,
    ProductResearchResponse,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=PipelineRunResponse)
def run_ingestion(
    request: PipelineRunRequest | None = None,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    return PipelineRunner(db).run(request or PipelineRunRequest())


@router.post("/refresh-existing", response_model=PipelineRunResponse)
def refresh_existing_products(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    return AmazonRefreshPipeline(db).run(limit=limit)


@router.post("/research", response_model=ProductResearchResponse)
def research_product(
    request: ProductResearchRequest,
    db: Session = Depends(get_db),
) -> ProductResearchResponse:
    canonical_name = " ".join(request.query.strip().lower().split())
    if not canonical_name:
        raise HTTPException(status_code=422, detail="Product name is required.")

    category = " ".join(request.category.strip().lower().split()) if request.category else None
    product = db.scalar(
        select(ProductCandidate)
        .where(func.lower(ProductCandidate.canonical_name) == canonical_name)
        .order_by(ProductCandidate.created_at.asc())
        .limit(1)
    )
    created = False
    if product is None:
        product = ProductCandidate(
            canonical_name=canonical_name,
            category=category,
            status=ProductStatus.CANDIDATE,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        created = True
    elif category and not product.category:
        product.category = category
        db.commit()
        db.refresh(product)

    pipeline = AmazonRefreshPipeline(db).run_product(product.id)
    return ProductResearchResponse(
        product_id=str(product.id),
        canonical_name=product.canonical_name,
        category=product.category,
        created=created,
        pipeline=pipeline,
    )
