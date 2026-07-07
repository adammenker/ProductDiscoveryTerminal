from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductListResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=ProductListResponse)
def list_opportunities(
    min_score: float | None = None,
    category: str | None = None,
    recommendation: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    items, total = ProductService(db).list_products(
        category=category,
        min_score=min_score,
        recommendation=recommendation,
        limit=limit,
        offset=offset,
        ranked=True,
    )
    return ProductListResponse(items=items, total=total)

