from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import RecommendationFeedback
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.schemas.product import (
    ComparableAsinUpdate,
    ProductDetailResponse,
    ProductListResponse,
    RecommendationFeedbackCreate,
)
from app.services.comparable_service import ComparableService
from app.services.product_service import ProductService
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    q: str | None = None,
    category: str | None = None,
    min_score: float | None = None,
    recommendation: str | None = None,
    eligible: bool | None = None,
    validation_decision: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    items, total = ProductService(db).list_products(
        q=q,
        category=category,
        min_score=min_score,
        recommendation=recommendation,
        eligible=eligible,
        validation_decision=validation_decision,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(items=items, total=total)


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    return ProductService(db).get_detail(product_id)


@router.get("/{product_id}/comparables")
def list_comparables(product_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    service = ComparableService(db)
    return [
        service.to_dict(row)
        for row in service.list_comparables(product_id)
    ]


@router.patch("/{product_id}/comparables/{asin}")
def update_comparable(
    product_id: UUID,
    asin: str,
    payload: ComparableAsinUpdate,
    db: Session = Depends(get_db),
) -> dict:
    service = ComparableService(db)
    row = service.update_relevance(
        product_id,
        asin,
        relevance_status=payload.relevance_status,
        reason=payload.reason,
    )
    if row.relevance_status == "manually_included":
        AmazonRefreshPipeline(db).run_product(product_id)
        rows = service.list_comparables(product_id, sync=False)
        row = next(item for item in rows if item.asin == asin.upper())
    else:
        ScoringService(db).score_product(product_id)
    return service.to_dict(row)


@router.get("/{product_id}/history")
def product_history(product_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    return ComparableService(db).history(product_id)


@router.get("/{product_id}/derived-signals")
def product_derived_signals(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    return ComparableService(db).derived_signals(product_id)


@router.post("/{product_id}/refresh")
def refresh_product(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    return AmazonRefreshPipeline(db).run_product(product_id).model_dump()


@router.post("/{product_id}/feedback", status_code=201)
def create_recommendation_feedback(
    product_id: UUID,
    payload: RecommendationFeedbackCreate,
    db: Session = Depends(get_db),
) -> dict:
    service = ProductService(db)
    product = service.get_detail(product_id)["product"]
    latest_score = service.latest_score(product_id)
    feedback = RecommendationFeedback(
        product_id=UUID(product["id"]),
        recommendation_snapshot_id=latest_score.id if latest_score else None,
        verdict=payload.verdict,
        reasons=payload.reasons,
        notes=payload.notes,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return _feedback_dict(feedback)


@router.get("/{product_id}/feedback")
def list_recommendation_feedback(product_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(RecommendationFeedback).filter(
        RecommendationFeedback.product_id == product_id
    ).order_by(RecommendationFeedback.created_at.desc()).all()
    return [_feedback_dict(row) for row in rows]


def _feedback_dict(feedback: RecommendationFeedback) -> dict:
    return {
        "id": str(feedback.id),
        "product_id": str(feedback.product_id),
        "recommendation_snapshot_id": (
            str(feedback.recommendation_snapshot_id)
            if feedback.recommendation_snapshot_id
            else None
        ),
        "verdict": feedback.verdict,
        "reasons": feedback.reasons,
        "notes": feedback.notes,
        "created_at": feedback.created_at,
    }
