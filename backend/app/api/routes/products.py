from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductDetailResponse, ProductListResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    q: str | None = None,
    category: str | None = None,
    min_score: float | None = None,
    recommendation: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    items, total = ProductService(db).list_products(
        q=q,
        category=category,
        min_score=min_score,
        recommendation=recommendation,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(items=items, total=total)


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: UUID, db: Session = Depends(get_db)) -> dict:
    return ProductService(db).get_detail(product_id)

