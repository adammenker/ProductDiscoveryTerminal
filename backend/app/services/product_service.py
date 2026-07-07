from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    CostModel,
    MarketSignal,
    OpportunityScore,
    ProductAlias,
    ProductCandidate,
    ProductInsight,
    RawObservation,
    Recommendation,
    SupplierSignal,
)
from app.schemas.plugin import ProductContext


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_products(
        self,
        q: str | None = None,
        category: str | None = None,
        min_score: float | None = None,
        recommendation: str | None = None,
        limit: int = 50,
        offset: int = 0,
        ranked: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[ProductCandidate]] = select(ProductCandidate)
        if q:
            pattern = f"%{q.lower()}%"
            stmt = stmt.outerjoin(ProductAlias).where(
                or_(
                    func.lower(ProductCandidate.canonical_name).like(pattern),
                    func.lower(ProductAlias.alias).like(pattern),
                )
            )
        if category:
            stmt = stmt.where(func.lower(ProductCandidate.category) == category.lower())
        products = list(self.db.scalars(stmt).unique().all())

        rows = [self._list_item(product) for product in products]
        if min_score is not None:
            rows = [row for row in rows if (row["latest_score"] or 0) >= min_score]
        if recommendation:
            rows = [row for row in rows if row["recommendation"] == recommendation]

        rows.sort(
            key=lambda row: (
                row["latest_score"] if row["latest_score"] is not None else -1,
                row["updated_at"],
            ),
            reverse=ranked,
        )
        if not ranked:
            rows.sort(key=lambda row: row["updated_at"], reverse=True)
        total = len(rows)
        return rows[offset : offset + limit], total

    def get_detail(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        product = self.db.get(ProductCandidate, uuid.UUID(str(product_id)))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        return {
            "product": {
                "id": str(product.id),
                "canonical_name": product.canonical_name,
                "category": product.category,
                "subcategory": product.subcategory,
                "description": product.description,
                "status": product.status.value,
                "created_at": product.created_at,
                "updated_at": product.updated_at,
            },
            "aliases": [self._alias_to_dict(alias) for alias in product.aliases],
            "latest_score": self._score_to_dict(self.latest_score(product.id)),
            "market_signals": [
                self._market_signal_to_dict(signal)
                for signal in self.db.scalars(
                    select(MarketSignal)
                    .where(MarketSignal.product_id == product.id)
                    .order_by(MarketSignal.created_at.desc())
                    .limit(100)
                )
            ],
            "supplier_signals": [
                self._supplier_signal_to_dict(signal)
                for signal in self.db.scalars(
                    select(SupplierSignal)
                    .where(SupplierSignal.product_id == product.id)
                    .order_by(SupplierSignal.created_at.desc())
                    .limit(50)
                )
            ],
            "cost_models": [
                self._cost_model_to_dict(cost_model)
                for cost_model in self.db.scalars(
                    select(CostModel)
                    .where(CostModel.product_id == product.id)
                    .order_by(CostModel.created_at.desc())
                    .limit(20)
                )
            ],
            "insights": [
                self._insight_to_dict(insight)
                for insight in self.db.scalars(
                    select(ProductInsight)
                    .where(ProductInsight.product_id == product.id)
                    .order_by(ProductInsight.created_at.desc())
                    .limit(100)
                )
            ],
            "recent_observations": [
                self._observation_to_dict(observation)
                for observation in self.db.scalars(
                    select(RawObservation)
                    .where(RawObservation.product_id == product.id)
                    .order_by(RawObservation.created_at.desc())
                    .limit(50)
                )
            ],
        }

    def build_context(self, product_id: uuid.UUID | str) -> ProductContext:
        product = self.db.get(ProductCandidate, uuid.UUID(str(product_id)))
        if product is None:
            raise ValueError(f"Product {product_id} not found")
        return ProductContext(
            product_id=str(product.id),
            canonical_name=product.canonical_name,
            category=product.category,
            observations=[
                self._observation_to_dict(observation)
                for observation in self.db.scalars(
                    select(RawObservation).where(RawObservation.product_id == product.id)
                )
            ],
            market_signals=[
                self._market_signal_to_dict(signal)
                for signal in self.db.scalars(
                    select(MarketSignal).where(MarketSignal.product_id == product.id)
                )
            ],
            supplier_signals=[
                self._supplier_signal_to_dict(signal)
                for signal in self.db.scalars(
                    select(SupplierSignal).where(SupplierSignal.product_id == product.id)
                )
            ],
            cost_models=[
                self._cost_model_to_dict(cost_model)
                for cost_model in self.db.scalars(select(CostModel).where(CostModel.product_id == product.id))
            ],
            insights=[
                self._insight_to_dict(insight)
                for insight in self.db.scalars(
                    select(ProductInsight).where(ProductInsight.product_id == product.id)
                )
            ],
        )

    def latest_score(self, product_id: uuid.UUID) -> OpportunityScore | None:
        return self.db.scalar(
            select(OpportunityScore)
            .where(OpportunityScore.product_id == product_id)
            .order_by(OpportunityScore.created_at.desc(), OpportunityScore.id.desc())
            .limit(1)
        )

    def _list_item(self, product: ProductCandidate) -> dict[str, Any]:
        latest = self.latest_score(product.id)
        latest_dict = self._score_to_dict(latest)
        return {
            "id": str(product.id),
            "canonical_name": product.canonical_name,
            "category": product.category,
            "status": product.status.value,
            "latest_score": latest_dict["final_score"] if latest_dict else None,
            "recommendation": latest_dict["recommendation"] if latest_dict else None,
            "demand_score": latest_dict["demand_score"] if latest_dict else None,
            "growth_score": latest_dict["growth_score"] if latest_dict else None,
            "competition_score": latest_dict["competition_score"] if latest_dict else None,
            "margin_score": latest_dict["margin_score"] if latest_dict else None,
            "pain_point_score": latest_dict["pain_point_score"] if latest_dict else None,
            "risk_score": latest_dict["risk_score"] if latest_dict else None,
            "confidence_score": latest_dict["confidence_score"] if latest_dict else None,
            "explanation": latest_dict["explanation"] if latest_dict else None,
            "updated_at": product.updated_at,
        }

    def _score_to_dict(self, score: OpportunityScore | None) -> dict[str, Any] | None:
        if score is None:
            return None
        return {
            "id": str(score.id),
            "product_id": str(score.product_id),
            "scoring_version": score.scoring_version,
            "demand_score": score.demand_score,
            "growth_score": score.growth_score,
            "competition_score": score.competition_score,
            "margin_score": score.margin_score,
            "pain_point_score": score.pain_point_score,
            "risk_score": score.risk_score,
            "confidence_score": score.confidence_score,
            "final_score": score.final_score,
            "recommendation": score.recommendation.value
            if isinstance(score.recommendation, Recommendation)
            else score.recommendation,
            "explanation": score.explanation,
            "score_breakdown": score.score_breakdown,
            "created_at": score.created_at,
        }

    @staticmethod
    def _alias_to_dict(alias: ProductAlias) -> dict[str, Any]:
        return {
            "id": str(alias.id),
            "alias": alias.alias,
            "source": alias.source,
            "confidence": alias.confidence,
            "created_at": alias.created_at,
        }

    @staticmethod
    def _observation_to_dict(observation: RawObservation) -> dict[str, Any]:
        return {
            "id": str(observation.id),
            "source": observation.source,
            "source_plugin": observation.source_plugin,
            "observed_at": observation.observed_at,
            "entity_type": observation.entity_type.value,
            "external_id": observation.external_id,
            "title": observation.title,
            "url": observation.url,
            "raw_text": observation.raw_text,
            "metrics": observation.metrics,
            "metadata": observation.metadata_,
            "media_urls": observation.media_urls,
            "content_hash": observation.content_hash,
            "created_at": observation.created_at,
        }

    @staticmethod
    def _market_signal_to_dict(signal: MarketSignal) -> dict[str, Any]:
        return {
            "id": str(signal.id),
            "source": signal.source,
            "signal_type": signal.signal_type.value,
            "value": signal.value,
            "unit": signal.unit,
            "window_start": signal.window_start,
            "window_end": signal.window_end,
            "metadata": signal.metadata_,
            "created_at": signal.created_at,
        }

    @staticmethod
    def _supplier_signal_to_dict(signal: SupplierSignal) -> dict[str, Any]:
        return {
            "id": str(signal.id),
            "source": signal.source,
            "supplier_name": signal.supplier_name,
            "supplier_url": signal.supplier_url,
            "unit_cost": signal.unit_cost,
            "moq": signal.moq,
            "lead_time_days": signal.lead_time_days,
            "shipping_estimate": signal.shipping_estimate,
            "country": signal.country,
            "metadata": signal.metadata_,
            "created_at": signal.created_at,
        }

    @staticmethod
    def _cost_model_to_dict(cost_model: CostModel) -> dict[str, Any]:
        return {
            "id": str(cost_model.id),
            "model_name": cost_model.model_name,
            "selling_price": cost_model.selling_price,
            "unit_cost": cost_model.unit_cost,
            "freight_cost_per_unit": cost_model.freight_cost_per_unit,
            "packaging_cost_per_unit": cost_model.packaging_cost_per_unit,
            "fulfillment_cost_per_unit": cost_model.fulfillment_cost_per_unit,
            "marketplace_fee_per_unit": cost_model.marketplace_fee_per_unit,
            "storage_cost_per_unit": cost_model.storage_cost_per_unit,
            "estimated_gross_margin": cost_model.estimated_gross_margin,
            "estimated_net_margin": cost_model.estimated_net_margin,
            "currency": cost_model.currency,
            "assumptions": cost_model.assumptions,
            "created_at": cost_model.created_at,
        }

    @staticmethod
    def _insight_to_dict(insight: ProductInsight) -> dict[str, Any]:
        return {
            "id": str(insight.id),
            "insight_type": insight.insight_type.value,
            "title": insight.title,
            "body": insight.body,
            "confidence": insight.confidence,
            "evidence_observation_ids": insight.evidence_observation_ids,
            "metadata": insight.metadata_,
            "created_at": insight.created_at,
        }
