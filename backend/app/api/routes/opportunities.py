from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductListResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("/buckets")
def opportunity_buckets(db: Session = Depends(get_db)) -> dict:
    rows, _ = ProductService(db).list_products(limit=1000, ranked=True)
    return {
        "strong_opportunities": [
            row for row in rows if row["validation_decision"] == "pursue"
        ],
        "needs_supplier_quote": [
            row
            for row in rows
            if row["supplier_validation_decision"] == "needs_supplier_quote"
        ],
        "above_cost_ceiling": [
            row
            for row in rows
            if row["supplier_validation_decision"] == "quote_above_ceiling"
        ],
        "constraint_failures": [
            row for row in rows if row["constraint_eligible"] is False
        ],
        "watchlist": [
            row for row in rows if row["validation_decision"] == "watch"
        ],
        "recently_discovered": sorted(
            rows,
            key=lambda row: row["updated_at"],
            reverse=True,
        )[:12],
    }


@router.get("", response_model=ProductListResponse)
def list_opportunities(
    min_score: float | None = None,
    category: str | None = None,
    recommendation: str | None = None,
    eligible: bool | None = None,
    validation_decision: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    items, total = ProductService(db).list_products(
        category=category,
        min_score=min_score,
        recommendation=recommendation,
        eligible=eligible,
        validation_decision=validation_decision,
        limit=limit,
        offset=offset,
        ranked=True,
    )
    return ProductListResponse(items=items, total=total)
