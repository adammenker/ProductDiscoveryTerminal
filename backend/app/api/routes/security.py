from __future__ import annotations

from fastapi import APIRouter

from app.security.compliance_check import compliance_status

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/compliance-status")
def get_compliance_status() -> dict:
    return compliance_status()
