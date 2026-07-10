from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.validation import (
    OutcomeCreate,
    PaperTradeCreate,
    SnapshotCreate,
    SnapshotTopRequest,
)
from app.services.backtest_service import BacktestService
from app.services.product_service import ProductService

router = APIRouter(tags=["backtests"])


@router.post("/products/{product_id}/snapshots", status_code=201)
def create_snapshot(
    product_id: UUID,
    payload: SnapshotCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = BacktestService(db)
    snapshot = service.create_snapshot(product_id, reason=payload.snapshot_reason)
    result: dict[str, Any] = {"snapshot": service.snapshot_dict(snapshot), "paper_trade": None}
    if payload.decision:
        trade = service.create_trade(
            product_id=product_id,
            snapshot_id=snapshot.id,
            decision=payload.decision,
            hypothesis=payload.hypothesis,
        )
        result["paper_trade"] = service.trade_dict(trade)
    return result


@router.post("/opportunities/snapshot-top", status_code=201)
def snapshot_top(
    payload: SnapshotTopRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows, _ = ProductService(db).list_products(
        min_score=payload.min_score,
        limit=payload.limit,
        ranked=True,
    )
    service = BacktestService(db)
    created = []
    for row in rows:
        snapshot = service.create_snapshot(row["id"], reason="snapshot_top")
        trade = service.create_trade(
            product_id=row["id"],
            snapshot_id=snapshot.id,
            decision=payload.decision,
            hypothesis=f"Frozen from top opportunities at score {row['latest_score']}.",
        )
        created.append(service.trade_dict(trade))
    return {"created": len(created), "paper_trades": created}


@router.get("/paper-trades")
def list_paper_trades(
    product_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return BacktestService(db).list_trades(product_id)


@router.post("/paper-trades", status_code=201)
def create_paper_trade(
    payload: PaperTradeCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = BacktestService(db)
    trade = service.create_trade(
        product_id=payload.product_id,
        snapshot_id=payload.snapshot_id,
        decision=payload.decision,
        hypothesis=payload.hypothesis,
        evaluation_windows=payload.evaluation_windows,
    )
    return service.trade_dict(trade)


@router.post("/paper-trades/{paper_trade_id}/outcomes", status_code=201)
def add_outcome(
    paper_trade_id: UUID,
    payload: OutcomeCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = BacktestService(db)
    outcome = service.add_outcome(paper_trade_id, payload.model_dump())
    return {
        "id": str(outcome.id),
        "paper_trade_id": str(outcome.paper_trade_id),
        "window_days": outcome.window_days,
        "measured_at": outcome.measured_at,
        "outcome_label": outcome.outcome_label,
        "outcome_score": outcome.outcome_score,
        "created_at": outcome.created_at,
    }


@router.get("/backtests/summary")
def backtest_summary(
    window_days: int | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return BacktestService(db).metrics(window_days)


@router.post("/backtests/run", status_code=201)
def run_backtest(
    window_days: int | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return BacktestService(db).metrics(window_days, persist=True)
