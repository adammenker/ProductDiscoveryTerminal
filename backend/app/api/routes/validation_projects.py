from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Supplier, ValidationRfq, ValidationSupplierQuote
from app.schemas.validation import (
    GateOverrideCreate,
    PoeEvidenceUpsert,
    RfqUpdate,
    SupplierCreate,
    SupplierUpdate,
    ValidationProjectCreate,
    ValidationProjectUpdate,
    ValidationQuoteCreate,
    ValidationQuoteUpdate,
    ValidationTransitionCreate,
)
from app.services.product_validation_service import ProductValidationService

router = APIRouter(tags=["validation-projects"])


@router.post("/validation-projects", status_code=201)
def create_project(
    payload: ValidationProjectCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    project = service.create_project(payload.model_dump())
    return service.project_dict(service.get_project(project.id), detail=True)


@router.get("/validation-projects")
def list_projects(status: str | None = None, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    service = ProductValidationService(db)
    return [
        service.project_dict(service.get_project(row.id)) for row in service.list_projects(status)
    ]


@router.get("/validation-projects/{project_id}")
def get_project(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    return service.project_dict(service.get_project(project_id), detail=True)


@router.patch("/validation-projects/{project_id}")
def update_project(
    project_id: UUID, payload: ValidationProjectUpdate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    return service.project_dict(service.get_project(project_id), detail=True)


@router.post("/validation-projects/{project_id}/transition")
def transition_project(
    project_id: UUID, payload: ValidationTransitionCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    service.transition(project_id, payload.to_status, payload.reason, payload.actor)
    return service.project_dict(service.get_project(project_id), detail=True)


@router.get("/validation-projects/{project_id}/marketplace-packets")
def list_packets(project_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    return [
        service.packet_dict(row)
        for row in sorted(project.packets, key=lambda row: row.version, reverse=True)
    ]


@router.get("/validation-projects/{project_id}/marketplace-packets/latest")
def latest_packet(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    packet = service.latest_packet(project_id)
    if packet is None:
        raise HTTPException(404, "Marketplace packet not found")
    return service.packet_dict(packet)


@router.post("/validation-projects/{project_id}/marketplace-packets/refresh")
def refresh_packet(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    return service.packet_dict(service.refresh_packet(project_id))


@router.get("/validation-projects/{project_id}/poe-evidence")
def get_poe(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any] | None:
    service = ProductValidationService(db)
    evidence = service.get_project(project_id).poe_evidence
    return service.poe_dict(evidence) if evidence else None


@router.put("/validation-projects/{project_id}/poe-evidence")
def put_poe(
    project_id: UUID, payload: PoeEvidenceUpsert, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    return service.poe_dict(service.upsert_poe(project_id, payload.model_dump(exclude_unset=True)))


@router.post("/validation-projects/{project_id}/rfqs/generate", status_code=201)
def generate_rfq(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    return service.rfq_dict(service.generate_rfq(project_id))


@router.get("/validation-projects/{project_id}/rfqs")
def list_rfqs(project_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    return [
        service.rfq_dict(row)
        for row in sorted(project.rfqs, key=lambda row: row.version, reverse=True)
    ]


@router.get("/validation-projects/{project_id}/rfqs/{rfq_id}")
def get_rfq(project_id: UUID, rfq_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    rfq = db.get(ValidationRfq, rfq_id)
    if rfq is None or rfq.validation_project_id != project.id:
        raise HTTPException(404, "RFQ not found")
    return service.rfq_dict(rfq)


@router.patch("/validation-projects/{project_id}/rfqs/{rfq_id}", status_code=201)
def revise_rfq(
    project_id: UUID, rfq_id: UUID, payload: RfqUpdate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    return service.rfq_dict(
        service.revise_rfq(project_id, rfq_id, payload.model_dump(exclude_unset=True))
    )


@router.post("/suppliers", status_code=201)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _supplier_dict(supplier)


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [_supplier_dict(row) for row in db.scalars(select(Supplier).order_by(Supplier.name))]


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(404, "Supplier not found")
    return _supplier_dict(supplier)


@router.patch("/suppliers/{supplier_id}")
def update_supplier(
    supplier_id: UUID, payload: SupplierUpdate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(404, "Supplier not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    db.commit()
    db.refresh(supplier)
    return _supplier_dict(supplier)


@router.post("/validation-projects/{project_id}/quotes", status_code=201)
def create_quote(
    project_id: UUID, payload: ValidationQuoteCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    quote = service.create_quote(project_id, payload.model_dump())
    return service.quote_dict(service.get_project(project_id), quote)


@router.get("/validation-projects/{project_id}/quotes")
def list_quotes(project_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    return [service.quote_dict(project, row) for row in project.quotes]


@router.get("/validation-projects/{project_id}/quotes/{quote_id}")
def get_quote(project_id: UUID, quote_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    quote = db.get(ValidationSupplierQuote, quote_id)
    if quote is None or quote.validation_project_id != project.id:
        raise HTTPException(404, "Quote not found")
    return service.quote_dict(project, quote)


@router.patch("/validation-projects/{project_id}/quotes/{quote_id}")
def update_quote(
    project_id: UUID, quote_id: UUID, payload: ValidationQuoteUpdate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    service = ProductValidationService(db)
    quote = service.update_quote(project_id, quote_id, payload.model_dump(exclude_unset=True))
    return service.quote_dict(service.get_project(project_id), quote)


@router.delete("/validation-projects/{project_id}/quotes/{quote_id}", status_code=204)
def delete_quote(project_id: UUID, quote_id: UUID, db: Session = Depends(get_db)) -> Response:
    service = ProductValidationService(db)
    project = service.get_project(project_id)
    quote = db.get(ValidationSupplierQuote, quote_id)
    if quote is None or quote.validation_project_id != project.id:
        raise HTTPException(404, "Quote not found")
    db.delete(quote)
    db.commit()
    return Response(status_code=204)


@router.post("/validation-projects/{project_id}/gates/evaluate")
def evaluate_gates(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    return ProductValidationService(db).evaluate_gates(project_id)


@router.get("/validation-projects/{project_id}/gates/latest")
def latest_gates(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    service = ProductValidationService(db)
    service.get_project(project_id)
    return service.latest_gates(project_id)


@router.post("/validation-projects/{project_id}/gates/{gate_name}/override")
def override_gate(
    project_id: UUID, gate_name: str, payload: GateOverrideCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    return ProductValidationService(db).override_gate(
        project_id, gate_name, payload.reason, payload.actor
    )


def _supplier_dict(s: Supplier) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "name": s.name,
        "platform": s.platform,
        "profile_url": s.profile_url,
        "location": s.location,
        "contact_name": s.contact_name,
        "contact_details": s.contact_details,
        "verified_status": s.verified_status,
        "years_in_business": s.years_in_business,
        "notes": s.notes,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }
