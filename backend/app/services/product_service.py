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
from app.services.comparable_service import AMAZON_COMPARABLE_PLUGINS, ComparableService


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_products(
        self,
        q: str | None = None,
        category: str | None = None,
        min_score: float | None = None,
        recommendation: str | None = None,
        eligible: bool | None = None,
        validation_decision: str | None = None,
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

        latest_scores = self._latest_scores({product.id for product in products})
        rows = [self._list_item(product, latest_scores.get(product.id)) for product in products]
        if min_score is not None:
            rows = [row for row in rows if (row["latest_score"] or 0) >= min_score]
        if recommendation:
            rows = [row for row in rows if row["recommendation"] == recommendation]
        if eligible is not None:
            rows = [row for row in rows if row["constraint_eligible"] is eligible]
        if validation_decision:
            rows = [row for row in rows if row["validation_decision"] == validation_decision]

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

        observations = [
            self._observation_to_dict(observation)
            for observation in self.db.scalars(
                select(RawObservation)
                .where(RawObservation.product_id == product.id)
                .order_by(RawObservation.created_at.desc())
                .limit(50)
            )
        ]
        from app.services.backtest_service import BacktestService
        from app.services.validation_service import ValidationService

        validation = ValidationService(self.db)
        comparable_service = ComparableService(self.db)
        comparable_service.sync_product(product.id, create_snapshots=False)
        economics = validation.economics(product.id)
        supplier = validation.supplier_validation(product.id)
        constraints = validation.latest_constraint(product.id)
        evidence = validation.evidence_matrix(product.id)
        decision = validation.decision(product.id)
        comparable_asins = [
            comparable_service.to_dict(row, economics.get("comparable_asin"))
            for row in comparable_service.list_comparables(product.id, sync=False)
        ]
        effective_comparables = [
            comparable_service.to_dict(row, economics.get("comparable_asin"))
            for row in comparable_service.get_effective_comparables(product.id)
        ]
        history = comparable_service.history(product.id)
        derived_signals = comparable_service.derived_signals(product.id)
        discovery_sources = sorted({item["source"] for item in observations})
        latest_score = self._score_to_dict(self.latest_score(product.id))
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
            "latest_score": latest_score,
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
            "recent_observations": observations,
            "discovery_source": {
                "sources": discovery_sources,
                "primary": discovery_sources[0] if discovery_sources else "manual",
                "last_updated": observations[0]["observed_at"] if observations else product.updated_at,
                "confidence": min(1.0, 0.45 + len(discovery_sources) * 0.1),
            },
            "comparable_asins": comparable_asins,
            "effective_comparables": effective_comparables,
            "comparable_summary": comparable_service.comparable_summary(product.id),
            "historical_summary": {
                "snapshot_count": len(history),
                "derived_signals": derived_signals,
            },
            "historical_signals": derived_signals,
            "marketplace_history": history[:100],
            "economics_validator": economics,
            "supplier_validation": supplier,
            "constraint_evaluation": constraints,
            "evidence_matrix": evidence["rows"],
            "cross_source_confidence_score": evidence["cross_source_confidence_score"],
            "missing_evidence": evidence["missing_evidence"],
            "validation_decision": decision,
            "recommendation_v2": _recommendation_v2(latest_score),
            "paper_trading_history": BacktestService(self.db).list_trades(product.id),
        }

    def build_context(self, product_id: uuid.UUID | str) -> ProductContext:
        product = self.db.get(ProductCandidate, uuid.UUID(str(product_id)))
        if product is None:
            raise ValueError(f"Product {product_id} not found")
        observations = self._current_observations(product.id)
        return ProductContext(
            product_id=str(product.id),
            canonical_name=product.canonical_name,
            category=product.category,
            observations=[
                self._observation_to_dict(observation)
                for observation in observations
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

    def _current_observations(self, product_id: uuid.UUID) -> list[RawObservation]:
        comparable_service = ComparableService(self.db)
        included_asins = comparable_service.included_asins(product_id)
        has_comparable_set = comparable_service.has_comparable_set(product_id)
        observations = self.db.scalars(
            select(RawObservation)
            .where(RawObservation.product_id == product_id)
            .order_by(
                RawObservation.observed_at.desc(),
                RawObservation.created_at.desc(),
                RawObservation.id.desc(),
            )
        )
        current: list[RawObservation] = []
        seen: set[tuple[str, str]] = set()
        for observation in observations:
            metadata = observation.metadata_ or {}
            asin = metadata.get("asin") or metadata.get("comparable_asin")
            if not asin and observation.external_id:
                asin = observation.external_id.split(":", 1)[0]
            if (
                has_comparable_set
                and _is_amazon_comparable_observation(observation)
                and asin
                and str(asin).upper().split(":", 1)[0] not in included_asins
            ):
                continue
            identity = (
                str(asin).upper()
                if asin
                else observation.external_id
                or observation.content_hash
            )
            key = (observation.source_plugin, identity)
            if key in seen:
                continue
            seen.add(key)
            current.append(observation)
        return current

    def latest_score(self, product_id: uuid.UUID) -> OpportunityScore | None:
        return self.db.scalar(
            select(OpportunityScore)
            .where(OpportunityScore.product_id == product_id)
            .order_by(OpportunityScore.created_at.desc(), OpportunityScore.id.desc())
            .limit(1)
        )

    def _latest_scores(
        self,
        product_ids: set[uuid.UUID],
    ) -> dict[uuid.UUID, OpportunityScore]:
        if not product_ids:
            return {}
        scores = self.db.scalars(
            select(OpportunityScore)
            .where(OpportunityScore.product_id.in_(product_ids))
            .order_by(
                OpportunityScore.product_id,
                OpportunityScore.created_at.desc(),
                OpportunityScore.id.desc(),
            )
        )
        latest: dict[uuid.UUID, OpportunityScore] = {}
        for score in scores:
            latest.setdefault(score.product_id, score)
        return latest

    def _list_item(
        self,
        product: ProductCandidate,
        latest: OpportunityScore | None = None,
    ) -> dict[str, Any]:
        latest_dict = self._score_to_dict(latest)
        validation = (latest_dict or {}).get("score_breakdown", {}).get("validation", {})
        return {
            "id": str(product.id),
            "canonical_name": product.canonical_name,
            "category": product.category,
            "status": product.status.value,
            "latest_score": latest_dict["final_score"] if latest_dict else None,
            "recommendation": latest_dict["recommendation"] if latest_dict else None,
            "opportunity_score": latest_dict.get("opportunity_score") if latest_dict else None,
            "evidence_confidence_score": latest_dict.get("evidence_confidence_score") if latest_dict else None,
            "validation_readiness_score": latest_dict.get("validation_readiness_score") if latest_dict else None,
            "scoring_version": latest_dict.get("scoring_version") if latest_dict else None,
            "demand_score": latest_dict["demand_score"] if latest_dict else None,
            "demand_proxy_score": latest_dict.get("demand_proxy_score") if latest_dict else None,
            "growth_score": latest_dict["growth_score"] if latest_dict else None,
            "competition_score": latest_dict["competition_score"] if latest_dict else None,
            "margin_score": latest_dict["margin_score"] if latest_dict else None,
            "pain_point_score": latest_dict["pain_point_score"] if latest_dict else None,
            "risk_score": latest_dict["risk_score"] if latest_dict else None,
            "confidence_score": latest_dict["confidence_score"] if latest_dict else None,
            "explanation": latest_dict["explanation"] if latest_dict else None,
            "economics_decision": validation.get("economics_decision"),
            "supplier_validation_decision": validation.get("supplier_validation_decision"),
            "constraint_eligible": validation.get("constraint_eligible"),
            "cross_source_confidence_score": validation.get("cross_source_confidence_score"),
            "validation_decision": validation.get("validation_decision"),
            "missing_evidence": validation.get("missing_evidence") or [],
            "updated_at": product.updated_at,
        }

    def _score_to_dict(self, score: OpportunityScore | None) -> dict[str, Any] | None:
        if score is None:
            return None
        breakdown = score.score_breakdown or {}
        opportunity_score = breakdown.get("opportunity_score", score.final_score)
        evidence_confidence_score = breakdown.get(
            "evidence_confidence_score",
            score.confidence_score,
        )
        validation_readiness_score = breakdown.get("validation_readiness_score")
        recommendation = breakdown.get("recommendation") or (
            score.recommendation.value
            if isinstance(score.recommendation, Recommendation)
            else score.recommendation
        )
        components = breakdown.get("components") or {}
        return {
            "id": str(score.id),
            "product_id": str(score.product_id),
            "scoring_version": score.scoring_version,
            "demand_score": score.demand_score,
            "demand_proxy_score": (components.get("demand_proxy") or {}).get("value", score.demand_score),
            "growth_score": score.growth_score,
            "competition_score": score.competition_score,
            "margin_score": score.margin_score,
            "pain_point_score": score.pain_point_score,
            "risk_score": score.risk_score,
            "confidence_score": score.confidence_score,
            "final_score": opportunity_score,
            "opportunity_score": opportunity_score,
            "evidence_confidence_score": evidence_confidence_score,
            "validation_readiness_score": validation_readiness_score,
            "recommendation": recommendation,
            "recommendation_reasons": breakdown.get("recommendation_reasons") or [],
            "missing_evidence": breakdown.get("missing_evidence") or [],
            "blocking_issues": breakdown.get("blocking_issues") or [],
            "next_actions": breakdown.get("next_actions") or [],
            "components": components,
            "explanation": score.explanation,
            "score_breakdown": breakdown,
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

    @staticmethod
    def _comparable_asins(
        observations: list[dict[str, Any]],
        selected_asin: str | None,
    ) -> list[dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for observation in observations:
            if "amazon" not in str(observation.get("source") or "").lower():
                continue
            metadata = observation.get("metadata") or {}
            external_id = str(observation.get("external_id") or "")
            asin = metadata.get("asin") or metadata.get("comparable_asin")
            if not asin and external_id:
                asin = external_id.split(":", 1)[0]
            if not asin:
                continue
            asin = str(asin).upper().split(":", 1)[0]
            metrics = observation.get("metrics") or {}
            row = rows.setdefault(
                asin,
                {
                    "asin": asin,
                    "title": None,
                    "url": f"https://www.amazon.com/dp/{asin}",
                    "price": None,
                    "fees": None,
                    "brand": None,
                    "sales_rank": None,
                    "review_count": None,
                    "source": observation.get("source"),
                    "observed_at": observation.get("observed_at"),
                    "selected_proxy": asin == selected_asin,
                },
            )
            evidence_type = metadata.get("evidence_type")
            if evidence_type == "amazon_catalog" or row["title"] is None:
                row["title"] = metadata.get("title") or observation.get("title")
                row["brand"] = metadata.get("brand") or row["brand"]
                row["sales_rank"] = (
                    metrics.get("bestseller_rank")
                    or metrics.get("sales_rank")
                    or row["sales_rank"]
                )
            if metrics.get("price") is not None:
                row["price"] = metrics["price"]
            if metrics.get("total_amazon_fees") is not None:
                row["fees"] = metrics["total_amazon_fees"]
            if metrics.get("review_count") is not None:
                row["review_count"] = metrics["review_count"]
            if observation.get("observed_at") and (
                row["observed_at"] is None
                or observation["observed_at"] > row["observed_at"]
            ):
                row["observed_at"] = observation["observed_at"]
        return sorted(rows.values(), key=lambda row: (not row["selected_proxy"], row["asin"]))


def _is_amazon_comparable_observation(observation: RawObservation) -> bool:
    evidence_type = (observation.metadata_ or {}).get("evidence_type")
    return observation.source_plugin in AMAZON_COMPARABLE_PLUGINS or evidence_type in {
        "amazon_catalog",
        "amazon_pricing",
        "amazon_fees",
    }


def _recommendation_v2(score: dict[str, Any] | None) -> dict[str, Any]:
    if not score:
        return {}
    return {
        "opportunity_score": score.get("opportunity_score"),
        "evidence_confidence_score": score.get("evidence_confidence_score"),
        "validation_readiness_score": score.get("validation_readiness_score"),
        "recommendation": score.get("recommendation"),
        "recommendation_reasons": score.get("recommendation_reasons") or [],
        "missing_evidence": score.get("missing_evidence") or [],
        "blocking_issues": score.get("blocking_issues") or [],
        "next_actions": score.get("next_actions") or [],
        "scoring_version": score.get("scoring_version"),
        "components": score.get("components") or {},
    }
