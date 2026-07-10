from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BacktestRun,
    OpportunitySnapshot,
    OutcomeMeasurement,
    PaperTrade,
    ProductCandidate,
)
from app.services.product_service import ProductService
from app.services.validation_service import ValidationService


class BacktestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.validation = ValidationService(db)

    def create_snapshot(
        self,
        product_id: uuid.UUID | str,
        *,
        reason: str = "manual",
    ) -> OpportunitySnapshot:
        product = self.db.get(ProductCandidate, uuid.UUID(str(product_id)))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        detail = ProductService(self.db).get_detail(product.id)
        score = detail.get("latest_score") or {}
        observations = detail.get("recent_observations") or []
        decision = self.validation.decision(product.id)
        snapshot = OpportunitySnapshot(
            product_id=product.id,
            snapshot_date=datetime.now(UTC),
            snapshot_reason=reason,
            discovery_source=observations[0]["source"] if observations else "manual",
            canonical_name=product.canonical_name,
            category=product.category,
            final_score=score.get("final_score"),
            recommendation=score.get("recommendation") or decision["decision"],
            component_scores=jsonable_encoder({
                key: value
                for key, value in score.items()
                if key.endswith("_score") or key == "final_score"
            }),
            cost_ceiling=jsonable_encoder(detail["economics_validator"]),
            supplier_validation=jsonable_encoder(detail["supplier_validation"]),
            constraint_evaluation=jsonable_encoder(detail["constraint_evaluation"]),
            evidence_matrix=jsonable_encoder(detail["evidence_matrix"]),
            thesis=decision["thesis"],
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def create_trade(
        self,
        *,
        product_id: uuid.UUID | str,
        snapshot_id: uuid.UUID | str,
        decision: str,
        hypothesis: str | None,
        evaluation_windows: list[int] | None = None,
    ) -> PaperTrade:
        snapshot = self.db.get(OpportunitySnapshot, uuid.UUID(str(snapshot_id)))
        if snapshot is None or str(snapshot.product_id) != str(product_id):
            raise HTTPException(status_code=404, detail="Snapshot not found for product")
        trade = PaperTrade(
            product_id=uuid.UUID(str(product_id)),
            snapshot_id=snapshot.id,
            decision=decision,
            hypothesis=hypothesis,
            entry_date=datetime.now(UTC),
            evaluation_windows=sorted(set(evaluation_windows or [30, 60, 90])),
            status="open",
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def add_outcome(self, trade_id: uuid.UUID | str, values: dict[str, Any]) -> OutcomeMeasurement:
        trade = self.db.get(PaperTrade, uuid.UUID(str(trade_id)))
        if trade is None:
            raise HTTPException(status_code=404, detail="Paper trade not found")
        outcome = OutcomeMeasurement(
            paper_trade_id=trade.id,
            window_days=values["window_days"],
            measured_at=values.get("measured_at") or datetime.now(UTC),
            price_change=values.get("price_change"),
            review_count_change=values.get("review_count_change"),
            rank_change=values.get("rank_change"),
            search_interest_change=values.get("search_interest_change"),
            seller_count_change=values.get("seller_count_change"),
            supplier_cost_change=values.get("supplier_cost_change"),
            constraint_status_change=values.get("constraint_status_change"),
            outcome_label=values["outcome_label"],
            outcome_score=values.get("outcome_score"),
            notes=values.get("notes"),
            metadata_=values.get("metadata") or {},
        )
        self.db.add(outcome)
        if values["window_days"] >= max(trade.evaluation_windows or [90]):
            trade.status = "evaluated"
        self.db.commit()
        self.db.refresh(outcome)
        return outcome

    def list_trades(self, product_id: uuid.UUID | str | None = None) -> list[dict[str, Any]]:
        stmt = select(PaperTrade).order_by(PaperTrade.created_at.desc())
        if product_id is not None:
            stmt = stmt.where(PaperTrade.product_id == uuid.UUID(str(product_id)))
        return [self.trade_dict(trade) for trade in self.db.scalars(stmt)]

    def metrics(self, window_days: int | None = None, *, persist: bool = False) -> dict[str, Any]:
        outcomes = list(self.db.scalars(select(OutcomeMeasurement)))
        if window_days is not None:
            outcomes = [item for item in outcomes if item.window_days == window_days]
        by_decision: dict[str, list[OutcomeMeasurement]] = defaultdict(list)
        by_source: dict[str, list[OutcomeMeasurement]] = defaultdict(list)
        for outcome in outcomes:
            by_decision[outcome.paper_trade.decision].append(outcome)
            source = outcome.paper_trade.snapshot.discovery_source or "unknown"
            by_source[source].append(outcome)

        def summary(items: list[OutcomeMeasurement]) -> dict[str, Any]:
            measured = [item for item in items if item.outcome_label != "insufficient_data"]
            improved = [item for item in measured if item.outcome_label == "improved"]
            scores = [item.outcome_score for item in measured if item.outcome_score is not None]
            return {
                "count": len(items),
                "measured_count": len(measured),
                "improved_rate": round(len(improved) / len(measured) * 100, 1) if measured else None,
                "average_outcome_score": round(sum(scores) / len(scores), 2) if scores else None,
            }

        metrics = {
            "total_paper_trades": self.db.query(PaperTrade).count(),
            "total_outcomes": len(outcomes),
            "top_picks_improved_rate": summary(by_decision.get("paper_pursue", []))["improved_rate"],
            "watch_picks_improved_rate": summary(by_decision.get("paper_watch", []))["improved_rate"],
            "skip_picks_improved_rate": summary(by_decision.get("paper_skip", []))["improved_rate"],
            "average_outcome_by_recommendation": {
                key: summary(items) for key, items in sorted(by_decision.items())
            },
            "average_outcome_by_discovery_source": {
                key: summary(items) for key, items in sorted(by_source.items())
            },
        }
        if persist:
            run = BacktestRun(
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                window_days=window_days,
                filters={"window_days": window_days},
                metrics=metrics,
            )
            self.db.add(run)
            self.db.commit()
        return metrics

    @staticmethod
    def snapshot_dict(snapshot: OpportunitySnapshot) -> dict[str, Any]:
        return {
            "id": str(snapshot.id),
            "product_id": str(snapshot.product_id),
            "snapshot_date": snapshot.snapshot_date,
            "snapshot_reason": snapshot.snapshot_reason,
            "discovery_source": snapshot.discovery_source,
            "canonical_name": snapshot.canonical_name,
            "category": snapshot.category,
            "final_score": snapshot.final_score,
            "recommendation": snapshot.recommendation,
            "component_scores": snapshot.component_scores,
            "cost_ceiling": snapshot.cost_ceiling,
            "supplier_validation": snapshot.supplier_validation,
            "constraint_evaluation": snapshot.constraint_evaluation,
            "evidence_matrix": snapshot.evidence_matrix,
            "thesis": snapshot.thesis,
            "created_at": snapshot.created_at,
        }

    @classmethod
    def trade_dict(cls, trade: PaperTrade) -> dict[str, Any]:
        return {
            "id": str(trade.id),
            "product_id": str(trade.product_id),
            "snapshot_id": str(trade.snapshot_id),
            "decision": trade.decision,
            "hypothesis": trade.hypothesis,
            "entry_date": trade.entry_date,
            "evaluation_windows": trade.evaluation_windows,
            "status": trade.status,
            "snapshot": cls.snapshot_dict(trade.snapshot),
            "outcomes": [
                {
                    "id": str(item.id),
                    "window_days": item.window_days,
                    "measured_at": item.measured_at,
                    "outcome_label": item.outcome_label,
                    "outcome_score": item.outcome_score,
                    "price_change": item.price_change,
                    "review_count_change": item.review_count_change,
                    "rank_change": item.rank_change,
                    "search_interest_change": item.search_interest_change,
                    "seller_count_change": item.seller_count_change,
                    "supplier_cost_change": item.supplier_cost_change,
                    "notes": item.notes,
                    "metadata": item.metadata_,
                }
                for item in sorted(trade.outcomes, key=lambda value: value.window_days)
            ],
            "created_at": trade.created_at,
        }
