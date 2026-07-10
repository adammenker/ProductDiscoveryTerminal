from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ProductCandidate, ProductStatus, RuleProfile, SupplierQuote
from app.schemas.validation import (
    ProductCreate,
    RuleProfileCreate,
    RuleProfileUpdate,
    SupplierQuoteCreate,
    SupplierQuoteUpdate,
    SupplierTextImport,
)
from app.services.scoring_service import ScoringService
from app.services.validation_service import ValidationService

router = APIRouter(tags=["validation"])


@router.post("/products", status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    product = ProductCandidate(
        canonical_name=payload.canonical_name.strip().lower(),
        category=payload.category.strip().lower() if payload.category else None,
        description=payload.description,
        status=ProductStatus.CANDIDATE,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return {
        "id": str(product.id),
        "canonical_name": product.canonical_name,
        "category": product.category,
        "status": product.status.value,
        "created_at": product.created_at,
    }


@router.get("/products/{product_id}/validation")
def get_validation(product_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ValidationService(db)
    return {
        "economics_validator": service.economics(product_id),
        "supplier_validation": service.supplier_validation(product_id),
        "constraint_evaluation": service.latest_constraint(product_id),
        "evidence_matrix": service.evidence_matrix(product_id),
        "validation_decision": service.decision(product_id),
    }


@router.get("/products/{product_id}/supplier-quotes")
def list_supplier_quotes(product_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return ValidationService(db).supplier_validation(product_id)["quotes"]


@router.post("/products/{product_id}/supplier-quotes", status_code=201)
def create_supplier_quote(
    product_id: UUID,
    payload: SupplierQuoteCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if db.get(ProductCandidate, product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    quote = SupplierQuote(
        product_id=product_id,
        source=payload.source,
        supplier_name=payload.supplier_name,
        supplier_url=payload.supplier_url,
        quote_date=payload.quote_date or datetime.now(UTC),
        unit_cost=payload.unit_cost,
        freight_cost_per_unit=payload.freight_cost_per_unit,
        packaging_cost_per_unit=payload.packaging_cost_per_unit,
        moq=payload.moq,
        lead_time_days=payload.lead_time_days,
        country=payload.country,
        currency=payload.currency.upper(),
        quote_status=payload.quote_status,
        confidence=payload.confidence,
        notes=payload.notes,
        metadata_=payload.metadata,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    ScoringService(db).score_product(product_id)
    service = ValidationService(db)
    return service.quote_dict(quote, (service.economics(product_id).get("modeled") or {}).get("max_landed_cost"))


@router.patch("/supplier-quotes/{quote_id}")
def update_supplier_quote(
    quote_id: UUID,
    payload: SupplierQuoteUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    quote = db.get(SupplierQuote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Supplier quote not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(quote, "metadata_" if key == "metadata" else key, value)
    db.commit()
    db.refresh(quote)
    ScoringService(db).score_product(quote.product_id)
    service = ValidationService(db)
    return service.quote_dict(
        quote,
        (service.economics(quote.product_id).get("modeled") or {}).get("max_landed_cost"),
    )


@router.delete("/supplier-quotes/{quote_id}", status_code=204)
def delete_supplier_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    quote = db.get(SupplierQuote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Supplier quote not found")
    db.delete(quote)
    db.commit()
    ScoringService(db).score_product(quote.product_id)
    return Response(status_code=204)


@router.post("/supplier-quotes/import-text", status_code=201)
def import_supplier_quote(
    payload: SupplierTextImport,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    product_id = UUID(payload.product_id)
    amount_matches = [
        float(value)
        for value in re.findall(r"\$\s*(\d+(?:\.\d{1,2})?)", payload.text)
    ]
    if not amount_matches:
        raise HTTPException(status_code=422, detail="Could not find a unit cost in pasted text")
    moq_match = re.search(r"\bMOQ\D{0,8}(\d+)", payload.text, flags=re.IGNORECASE)
    freight_match = re.search(
        r"(?:freight|shipping)\D{0,12}\$\s*(\d+(?:\.\d{1,2})?)",
        payload.text,
        flags=re.IGNORECASE,
    )
    packaging_match = re.search(
        r"packag(?:e|ing)\D{0,12}\$\s*(\d+(?:\.\d{1,2})?)",
        payload.text,
        flags=re.IGNORECASE,
    )
    supplier_match = re.search(r"supplier\s+([^,:]+)", payload.text, flags=re.IGNORECASE)
    quote_payload = SupplierQuoteCreate(
        source=payload.source,
        supplier_name=supplier_match.group(1).strip() if supplier_match else None,
        quote_date=datetime.now(UTC),
        unit_cost=amount_matches[0],
        freight_cost_per_unit=float(freight_match.group(1)) if freight_match else None,
        packaging_cost_per_unit=float(packaging_match.group(1)) if packaging_match else None,
        moq=int(moq_match.group(1)) if moq_match else None,
        quote_status="parsed",
        confidence=0.65,
        notes=payload.text,
        metadata={"parser": "manual_quote_regex_v1"},
    )
    return create_supplier_quote(product_id, quote_payload, db)


@router.get("/rule-profiles")
def list_rule_profiles(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    ValidationService(db).default_profile()
    return [_profile_dict(profile) for profile in db.scalars(select(RuleProfile))]


@router.get("/rule-profiles/{profile_id}")
def get_rule_profile(profile_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = db.get(RuleProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Rule profile not found")
    return _profile_dict(profile)


@router.post("/rule-profiles", status_code=201)
def create_rule_profile(
    payload: RuleProfileCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.is_default:
        for profile in db.scalars(select(RuleProfile).where(RuleProfile.is_default.is_(True))):
            profile.is_default = False
    profile = RuleProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_dict(profile)


@router.patch("/rule-profiles/{profile_id}")
def update_rule_profile(
    profile_id: UUID,
    payload: RuleProfileUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = db.get(RuleProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Rule profile not found")
    values = payload.model_dump(exclude_unset=True)
    if values.get("is_default"):
        for current in db.scalars(select(RuleProfile).where(RuleProfile.is_default.is_(True))):
            current.is_default = False
    for key, value in values.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return _profile_dict(profile)


@router.post("/products/{product_id}/evaluate-constraints")
def evaluate_constraints(
    product_id: UUID,
    profile_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = ValidationService(db).evaluate_constraints(product_id, profile_id)
    ScoringService(db).score_product(product_id)
    return result


def _profile_dict(profile: RuleProfile) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "name": profile.name,
        "is_default": profile.is_default,
        "hard_rules": profile.hard_rules,
        "soft_rules": profile.soft_rules,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
