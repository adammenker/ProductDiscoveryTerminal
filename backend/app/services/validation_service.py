from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from statistics import median_high
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.economics.cost_ceiling import calculate_cost_ceiling_v2
from app.models import (
    ConstraintEvaluation,
    CostModel,
    MarketSignal,
    ProductCandidate,
    ProductInsight,
    RawObservation,
    RuleProfile,
    SupplierQuote,
)

DEFAULT_HARD_RULES = {
    "exclude_batteries": True,
    "exclude_supplements": True,
    "exclude_ingestibles": True,
    "exclude_liquids": True,
    "exclude_fragile_glass": True,
    "exclude_weapons": True,
    "min_selling_price": 20,
    "max_selling_price": 50,
    "min_target_margin": 30,
}
DEFAULT_SOFT_RULES = {
    "prefer_weight_under_lb": 1.5,
    "prefer_review_count_under": 500,
    "prefer_moq_under": 1000,
    "penalize_brand_dominance": True,
}

RISK_PATTERNS = {
    "battery": (r"\bbatter(?:y|ies)\b|lithium|rechargeable", "high"),
    "liquid": (r"\b(?:liquid|serum|oil|fluid|gel)\b", "high"),
    "supplement": (r"\b(?:supplement|vitamin|gummy|capsule|ingestible)\b", "high"),
    "medical_claim": (r"\b(?:cure|treats?|treatment|medical|therapy)\b", "medium"),
    "fragile": (r"\bglass\b|ceramic|fragile", "high"),
    "oversized": (r"\boversized\b|extra large|heavy duty", "medium"),
    "electronics": (r"\b(?:electronic|electric|usb|charger)\b", "medium"),
    "children_product": (r"\b(?:child|children|kid|baby|infant)\b", "medium"),
    "skin_contact": (r"\b(?:skin|facial|face|derma)\b", "low"),
    "food_contact": (r"\b(?:food|kitchen|utensil|bottle)\b", "low"),
    "trademark_brand_risk": (r"\bcompatible with\b|replacement for", "medium"),
    "high_return_risk": (r"\b(?:sizing|fit|apparel|shoe)\b", "medium"),
    "seasonal": (r"\b(?:christmas|halloween|holiday|seasonal)\b", "medium"),
    "weapon": (r"\b(?:weapon|knife|blade|firearm)\b", "high"),
}


class ValidationService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def economics(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        product = self._product(product_id)
        prices = self._prices(product.id)
        modeled_price = round(float(median_high(prices)), 2) if prices else None
        fee_source, fee_confidence, amazon_fees, comparable_asin = self._fees(product.id, modeled_price)
        quote = self.best_quote(product.id)
        result = calculate_cost_ceiling_v2(
            selling_price=modeled_price,
            amazon_fees=amazon_fees,
            inbound_cost_per_unit=self.settings.cost_ceiling_inbound_cost_per_unit,
            storage_estimate=self.settings.cost_ceiling_storage_cost_per_unit,
            return_allowance_rate=self.settings.cost_ceiling_return_allowance_rate,
            ad_allowance_rate=self.settings.cost_ceiling_ad_allowance_rate,
            supplier_unit_cost=quote.unit_cost if quote else None,
            supplier_freight_cost_per_unit=quote.freight_cost_per_unit if quote else None,
            packaging_cost_per_unit=(
                quote.packaging_cost_per_unit
                if quote and quote.packaging_cost_per_unit is not None
                else self.settings.cost_ceiling_packaging_cost_per_unit
            ),
            selling_price_range=(
                (round(min(prices), 2), modeled_price, round(max(prices), 2))
                if prices and modeled_price is not None
                else None
            ),
        )
        warnings = []
        if fee_source != "amazon_spapi_product_fees":
            warnings.append("Amazon fees use configurable estimates until Product Fees access succeeds.")
        elif comparable_asin:
            warnings.append("Estimated from comparable ASINs, not guaranteed actual fees.")
        if quote is None:
            warnings.append("A supplier quote is required to validate sourcing economics.")
        assumptions = {
            "target_margins": [20, 30, 40, 50],
            "inbound_cost_per_unit": self.settings.cost_ceiling_inbound_cost_per_unit,
            "storage_estimate": self.settings.cost_ceiling_storage_cost_per_unit,
            "return_allowance_rate": self.settings.cost_ceiling_return_allowance_rate,
            "ad_allowance_rate": self.settings.cost_ceiling_ad_allowance_rate,
            "packaging_fallback_per_unit": self.settings.cost_ceiling_packaging_cost_per_unit,
        }
        return {
            **result,
            "modeled_price": modeled_price,
            "price_range": {
                "low": round(min(prices), 2) if prices else None,
                "modeled": modeled_price,
                "high": round(max(prices), 2) if prices else None,
            },
            "fee_source": fee_source,
            "fee_source_confidence": fee_confidence,
            "amazon_fees": amazon_fees,
            "comparable_asin": comparable_asin,
            "assumptions": assumptions,
            "warnings": warnings,
            "updated_at": datetime.now(UTC),
        }

    def supplier_validation(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        product = self._product(product_id)
        economics = self.economics(product.id)
        modeled = economics.get("modeled") or {}
        ceiling = modeled.get("max_landed_cost")
        quotes = list(
            self.db.scalars(
                select(SupplierQuote)
                .where(SupplierQuote.product_id == product.id)
                .order_by(SupplierQuote.created_at.desc())
            )
        )
        rows = [self.quote_dict(quote, ceiling) for quote in quotes]
        viable = [row for row in rows if row["decision"] == "quote_at_or_below_ceiling"]
        score = 20.0
        if len(viable) >= 2:
            score = 100.0
        elif viable:
            score = 80.0
        elif rows and ceiling and any(abs(row["margin_of_safety"] or 0) <= ceiling * 0.1 for row in rows):
            score = 60.0
        elif rows:
            score = 25.0
        if rows:
            score -= min(
                25,
                max((15 if (row.get("moq") or 0) > 1000 else 0) for row in rows)
                + max((10 if (row.get("lead_time_days") or 0) > 60 else 0) for row in rows),
            )
        return {
            "quotes": rows,
            "supplier_validation_score": max(0.0, round(score, 1)),
            "viable_quote_count": len(viable),
            "decision": (
                "quote_at_or_below_ceiling"
                if viable
                else "quote_above_ceiling"
                if rows
                else "needs_supplier_quote"
            ),
            "max_landed_cost": ceiling,
            "source": "supplier_quotes",
            "updated_at": datetime.now(UTC),
        }

    def default_profile(self) -> RuleProfile:
        profile = self.db.scalar(select(RuleProfile).where(RuleProfile.is_default.is_(True)).limit(1))
        if profile is None:
            profile = RuleProfile(
                name="Adam Conservative FBA Filter",
                is_default=True,
                hard_rules=DEFAULT_HARD_RULES,
                soft_rules=DEFAULT_SOFT_RULES,
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def evaluate_constraints(
        self,
        product_id: uuid.UUID | str,
        profile_id: uuid.UUID | str | None = None,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        product = self._product(product_id)
        profile = (
            self.db.get(RuleProfile, uuid.UUID(str(profile_id)))
            if profile_id
            else self.default_profile()
        )
        if profile is None:
            raise HTTPException(status_code=404, detail="Rule profile not found")
        text, evidence = self._risk_text(product.id, product)
        flags = []
        for risk_type, (pattern, severity) in RISK_PATTERNS.items():
            matches = sorted(set(re.findall(pattern, text, flags=re.IGNORECASE)))
            if not matches:
                continue
            flags.append(
                {
                    "risk_type": risk_type,
                    "severity": severity,
                    "confidence": 0.8 if risk_type in {"battery", "liquid", "supplement", "fragile"} else 0.65,
                    "evidence": matches[:5],
                    "source": evidence,
                }
            )
        flag_types = {flag["risk_type"] for flag in flags}
        rules = profile.hard_rules
        mapping = {
            "exclude_batteries": "battery",
            "exclude_supplements": "supplement",
            "exclude_ingestibles": "supplement",
            "exclude_liquids": "liquid",
            "exclude_fragile_glass": "fragile",
            "exclude_weapons": "weapon",
        }
        hard_failures = [
            {
                "rule": rule,
                "risk_type": risk_type,
                "message": f"Hard rule failed: {risk_type}.",
            }
            for rule, risk_type in mapping.items()
            if rules.get(rule) and risk_type in flag_types
        ]
        economics = self.economics(product.id)
        price = economics.get("modeled_price")
        soft_warnings: list[dict[str, Any]] = []
        if price is not None and (
            price < float(rules.get("min_selling_price", 0))
            or price > float(rules.get("max_selling_price", 10_000))
        ):
            soft_warnings.append(
                {"rule": "preferred_selling_price", "message": "Modeled price is outside $20-$50."}
            )
        quote = self.best_quote(product.id)
        prefer_moq = profile.soft_rules.get("prefer_moq_under")
        if quote and prefer_moq and quote.moq and quote.moq > int(prefer_moq):
            soft_warnings.append(
                {"rule": "prefer_moq_under", "message": f"MOQ {quote.moq} exceeds {prefer_moq}."}
            )
        score = max(0.0, 100.0 - 35 * len(hard_failures) - 10 * len(soft_warnings))
        eligible = not hard_failures
        explanation = (
            f"Passes {profile.name}."
            if eligible
            else f"Fails {profile.name}: " + ", ".join(item["risk_type"] for item in hard_failures) + "."
        )
        payload = {
            "rule_profile_id": str(profile.id),
            "rule_profile_name": profile.name,
            "hard_failures": hard_failures,
            "soft_warnings": soft_warnings,
            "risk_flags": flags,
            "constraint_score": score,
            "eligible": eligible,
            "explanation": explanation,
            "created_at": datetime.now(UTC),
        }
        if persist:
            evaluation = ConstraintEvaluation(
                product_id=product.id,
                rule_profile_id=profile.id,
                hard_failures=hard_failures,
                soft_warnings=soft_warnings,
                risk_flags=flags,
                constraint_score=score,
                eligible=eligible,
                explanation=explanation,
            )
            self.db.add(evaluation)
            self.db.commit()
            self.db.refresh(evaluation)
            payload["id"] = str(evaluation.id)
            payload["created_at"] = evaluation.created_at
        return payload

    def latest_constraint(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        product = self._product(product_id)
        evaluation = self.db.scalar(
            select(ConstraintEvaluation)
            .where(ConstraintEvaluation.product_id == product.id)
            .order_by(ConstraintEvaluation.created_at.desc(), ConstraintEvaluation.id.desc())
            .limit(1)
        )
        if evaluation is None:
            return self.evaluate_constraints(product.id, persist=False)
        return {
            "id": str(evaluation.id),
            "rule_profile_id": str(evaluation.rule_profile_id),
            "rule_profile_name": evaluation.rule_profile.name,
            "hard_failures": evaluation.hard_failures,
            "soft_warnings": evaluation.soft_warnings,
            "risk_flags": evaluation.risk_flags,
            "constraint_score": evaluation.constraint_score,
            "eligible": evaluation.eligible,
            "explanation": evaluation.explanation,
            "created_at": evaluation.created_at,
        }

    def evidence_matrix(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        product = self._product(product_id)
        observations = list(
            self.db.scalars(select(RawObservation).where(RawObservation.product_id == product.id))
        )
        economics = self.economics(product.id)
        supplier = self.supplier_validation(product.id)
        constraints = self.latest_constraint(product.id)
        sources = sorted({item.source for item in observations})
        amazon_obs = [item for item in observations if "amazon" in item.source.lower()]
        pain = list(
            self.db.scalars(
                select(ProductInsight).where(
                    ProductInsight.product_id == product.id,
                    ProductInsight.insight_type.in_(["complaint_cluster", "feature_gap", "review_summary"]),
                )
            )
        )
        external = [
            item
            for item in observations
            if any(token in item.source.lower() for token in ("reddit", "trend", "manual", "etsy"))
        ]
        prices = self._prices(product.id)
        stale_observations = [
            item
            for item in observations
            if item.observed_at.tzinfo
            and (datetime.now(UTC) - item.observed_at).days > 90
        ]
        conflicting_prices = bool(
            len(prices) >= 2 and min(prices) > 0 and max(prices) / min(prices) >= 1.5
        )
        has_valid_fee_source = economics.get("fee_source") != "configurable_defaults"
        rows = [
            self._evidence_row("Discovery Source", bool(observations), len(sources), "Candidate source coverage."),
            self._evidence_row("Amazon Demand", bool(amazon_obs), len(amazon_obs), "Amazon observations found."),
            self._evidence_row(
                "Amazon Competition",
                any((item.metrics or {}).get("seller_count") is not None for item in amazon_obs),
                len(amazon_obs),
                "Seller and review competition evidence.",
            ),
            self._evidence_row(
                "Amazon Pricing",
                economics.get("modeled_price") is not None,
                len(self._prices(product.id)),
                f"Modeled sale price: {economics.get('modeled_price') or 'missing'}.",
            ),
            self._evidence_row(
                "Amazon Fees",
                has_valid_fee_source,
                1 if has_valid_fee_source else 0,
                f"Fee source: {economics.get('fee_source')}.",
            ),
            self._evidence_row(
                "Supplier Quotes",
                bool(supplier["quotes"]),
                len(supplier["quotes"]),
                f"{supplier['viable_quote_count']} quote(s) below ceiling.",
                negative=bool(supplier["quotes"]) and not supplier["viable_quote_count"],
            ),
            self._evidence_row("Customer Pain", bool(pain), len(pain), "Complaint and feature-gap evidence."),
            self._evidence_row(
                "Trend/Social Interest",
                bool(external),
                len(external),
                "Independent non-Amazon observations.",
            ),
            self._evidence_row(
                "Constraint Fit",
                bool(constraints["eligible"]),
                len(constraints["risk_flags"]),
                constraints["explanation"],
                negative=not constraints["eligible"],
            ),
            self._evidence_row("Backtest/Paper History", False, 0, "No measured history yet."),
        ]
        score = 0
        score += 20 if amazon_obs else 0
        score += 15 if economics.get("modeled_price") is not None else 0
        score += 15 if has_valid_fee_source else 0
        score += 20 if supplier["quotes"] else 0
        score += 10 if supplier["viable_quote_count"] else 0
        score += 10 if pain else 0
        score += 10 if external else 0
        score += 10 if constraints["eligible"] else 0
        if any(row["direction"] == "negative" for row in rows):
            score -= 20
        if stale_observations:
            score -= 20
        if conflicting_prices:
            score -= 20
        score = max(0, min(100, score))
        missing = []
        if not supplier["quotes"]:
            missing.append("Need supplier quote")
        if economics.get("fee_source") != "amazon_spapi_product_fees":
            missing.append("Need live Amazon fee estimate")
        if not external:
            missing.append("Need non-Amazon trend signal")
        if not pain:
            missing.append("Need customer pain evidence")
        if stale_observations:
            missing.append("Refresh stale evidence")
        if conflicting_prices:
            missing.append("Resolve conflicting price evidence")
        return {
            "rows": rows,
            "cross_source_confidence_score": score,
            "missing_evidence": missing,
            "sources": sources,
            "updated_at": datetime.now(UTC),
        }

    def decision(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        product = self._product(product_id)
        economics = self.economics(product.id)
        supplier = self.supplier_validation(product.id)
        constraints = self.latest_constraint(product.id)
        evidence = self.evidence_matrix(product.id)
        economics_decision = economics.get("decision")
        if not constraints["eligible"] or economics_decision in {
            "quote_above_ceiling",
            "invalid_negative_ceiling",
        }:
            decision = "skip"
        elif (
            supplier["viable_quote_count"]
            and evidence["cross_source_confidence_score"] >= 70
            and economics_decision == "quote_at_or_below_ceiling"
            and economics.get("fee_source") != "configurable_defaults"
        ):
            decision = "pursue"
        elif economics_decision == "needs_supplier_quote" or evidence["missing_evidence"]:
            decision = "investigate"
        else:
            decision = "watch"
        thesis = self._thesis(product, economics, supplier, constraints, evidence, decision)
        return {
            "decision": decision,
            "thesis": thesis,
            "cross_source_confidence_score": evidence["cross_source_confidence_score"],
            "missing_evidence": evidence["missing_evidence"],
        }

    def best_quote(self, product_id: uuid.UUID | str) -> SupplierQuote | None:
        quotes = list(
            self.db.scalars(
                select(SupplierQuote).where(
                    SupplierQuote.product_id == uuid.UUID(str(product_id)),
                    SupplierQuote.quote_status.notin_(["rejected", "expired"]),
                )
            )
        )
        return min(quotes, key=self.landed_cost) if quotes else None

    @staticmethod
    def landed_cost(quote: SupplierQuote) -> float:
        return round(
            quote.unit_cost
            + (quote.freight_cost_per_unit or 0)
            + (quote.packaging_cost_per_unit or 0),
            2,
        )

    def quote_dict(self, quote: SupplierQuote, ceiling: float | None = None) -> dict[str, Any]:
        landed = self.landed_cost(quote)
        age_days = (
            (datetime.now(UTC) - quote.quote_date).days
            if quote.quote_date and quote.quote_date.tzinfo
            else None
        )
        expired = age_days is not None and age_days > 90
        status = "expired" if expired else quote.quote_status
        margin = round(ceiling - landed, 2) if ceiling is not None else None
        decision = (
            "needs_supplier_quote"
            if ceiling is None
            else "quote_at_or_below_ceiling"
            if landed <= ceiling
            else "quote_above_ceiling"
        )
        return {
            "id": str(quote.id),
            "product_id": str(quote.product_id),
            "source": quote.source,
            "supplier_name": quote.supplier_name,
            "supplier_url": quote.supplier_url,
            "quote_date": quote.quote_date,
            "unit_cost": quote.unit_cost,
            "freight_cost_per_unit": quote.freight_cost_per_unit,
            "packaging_cost_per_unit": quote.packaging_cost_per_unit,
            "supplier_landed_cost": landed,
            "max_landed_cost": ceiling,
            "margin_of_safety": margin,
            "decision": decision,
            "moq": quote.moq,
            "lead_time_days": quote.lead_time_days,
            "country": quote.country,
            "currency": quote.currency,
            "quote_status": status,
            "confidence": quote.confidence,
            "notes": quote.notes,
            "metadata": quote.metadata_,
            "age_days": age_days,
            "created_at": quote.created_at,
            "updated_at": quote.updated_at,
        }

    def _product(self, product_id: uuid.UUID | str) -> ProductCandidate:
        product = self.db.get(ProductCandidate, uuid.UUID(str(product_id)))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def _prices(self, product_id: uuid.UUID) -> list[float]:
        values: list[float] = []
        seen: set[tuple[str, str]] = set()
        observations = self.db.scalars(
            select(RawObservation)
            .where(RawObservation.product_id == product_id)
            .order_by(
                RawObservation.observed_at.desc(),
                RawObservation.created_at.desc(),
                RawObservation.id.desc(),
            )
        )
        for observation in observations:
            price = (observation.metrics or {}).get("price")
            if price is None or float(price) <= 0:
                continue
            metadata = observation.metadata_ or {}
            asin = metadata.get("asin") or metadata.get("comparable_asin")
            identity = str(asin).upper() if asin else observation.external_id or observation.content_hash
            key = (observation.source_plugin, identity)
            if key in seen:
                continue
            seen.add(key)
            values.append(float(price))
        if values:
            return values
        return [
            signal.value
            for signal in self.db.scalars(
                select(MarketSignal)
                .where(
                    MarketSignal.product_id == product_id,
                    MarketSignal.signal_type == "price",
                )
                .order_by(MarketSignal.created_at.desc(), MarketSignal.id.desc())
            )
            if signal.value > 0
        ]

    def _fees(
        self,
        product_id: uuid.UUID,
        modeled_price: float | None,
    ) -> tuple[str, str, float | None, str | None]:
        models = list(
            self.db.scalars(
                select(CostModel)
                .where(CostModel.product_id == product_id)
                .order_by(CostModel.created_at.desc())
            )
        )
        priority = (
            ("amazon_fba_fee_estimate", "amazon_spapi_product_fees", "high"),
            ("manual_amazon_fee_estimate", "manual_amazon_fee_estimate", "medium"),
            ("third_party_fee_estimate", "third_party_fee_estimate", "medium"),
        )
        for model_name, source, confidence in priority:
            candidates = [item for item in models if item.model_name == model_name]
            if not candidates:
                continue
            model = (
                min(candidates, key=lambda item: abs(item.selling_price - modeled_price))
                if modeled_price is not None
                else candidates[0]
            )
            component_fees = [
                value
                for value in (
                    model.marketplace_fee_per_unit,
                    model.fulfillment_cost_per_unit,
                )
                if value is not None
            ]
            total_fees = model.assumptions.get("total_amazon_fees")
            if not component_fees and total_fees is None:
                continue
            fees = float(total_fees) if total_fees is not None else sum(component_fees)
            comparable_asin = model.assumptions.get("comparable_asin")
            return source, confidence, round(fees, 2), comparable_asin
        if modeled_price is None:
            return "configurable_defaults", "low", None, None
        marketplace = modeled_price * self.settings.cost_ceiling_marketplace_fee_rate
        fulfillment = max(
            self.settings.cost_ceiling_fulfillment_fee_floor,
            modeled_price * self.settings.cost_ceiling_fulfillment_fee_rate,
        )
        return "configurable_defaults", "low", round(marketplace + fulfillment, 2), None

    def _risk_text(
        self,
        product_id: uuid.UUID,
        product: ProductCandidate,
    ) -> tuple[str, list[str]]:
        observations = list(
            self.db.scalars(select(RawObservation).where(RawObservation.product_id == product_id))
        )
        parts = [product.canonical_name, product.category or "", product.description or ""]
        sources = []
        for item in observations:
            parts.extend([item.title or "", item.raw_text or ""])
            sources.append(item.source)
        return " ".join(parts), sorted(set(sources)) or ["product_candidate"]

    @staticmethod
    def _evidence_row(
        area: str,
        available: bool,
        count: int,
        notes: str,
        *,
        negative: bool = False,
    ) -> dict[str, Any]:
        direction = "negative" if negative else "positive" if available else "missing"
        return {
            "area": area,
            "signal": "available" if available else "missing",
            "source_count": count,
            "strength": min(100, 55 + count * 8) if available else 0,
            "direction": direction,
            "freshness_days": 0 if available else None,
            "confidence": min(95, 50 + count * 10) if available else 0,
            "evidence_links": [],
            "notes": notes,
        }

    @staticmethod
    def _thesis(
        product: ProductCandidate,
        economics: dict[str, Any],
        supplier: dict[str, Any],
        constraints: dict[str, Any],
        evidence: dict[str, Any],
        decision: str,
    ) -> str:
        modeled = economics.get("modeled") or {}
        ceiling = modeled.get("max_landed_cost")
        return (
            f"{product.canonical_name} has a {decision} recommendation with "
            f"{evidence['cross_source_confidence_score']}/100 cross-source confidence. "
            f"The modeled sale price is ${economics.get('modeled_price') or 0:.2f}; "
            f"at a 30% target margin, fully landed cost must be at or below "
            f"${ceiling or 0:.2f}/unit. {supplier['viable_quote_count']} supplier quote(s) "
            f"currently clear that ceiling. Constraint fit is "
            f"{'eligible' if constraints['eligible'] else 'ineligible'} under "
            f"{constraints['rule_profile_name']}."
        )
