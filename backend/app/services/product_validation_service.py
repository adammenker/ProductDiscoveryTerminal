from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models import (
    ConstraintEvaluation,
    OpportunityScore,
    ProductCandidate,
    ProductValidationProject,
    Supplier,
    SupplierQuoteTier,
    ValidationGateEvaluation,
    ValidationMarketplacePacket,
    ValidationPoeEvidence,
    ValidationRfq,
    ValidationSupplierQuote,
    ValidationTransition,
)
from app.pipeline.amazon_refresh import AmazonRefreshPipeline
from app.services.comparable_service import ComparableService
from app.services.scoring_service import ScoringService
from app.services.validation_service import ValidationService

ACTIVE_STATUSES = {
    "draft",
    "marketplace_validation",
    "sourcing",
    "ready_for_decision",
    "approved_for_sample",
}
TRANSITIONS = {
    "draft": {"marketplace_validation"},
    "marketplace_validation": {"sourcing", "rejected"},
    "sourcing": {"ready_for_decision", "rejected"},
    "ready_for_decision": {"approved_for_sample", "sourcing", "rejected"},
    "approved_for_sample": {"archived"},
    "rejected": {"marketplace_validation", "archived"},
    "archived": set(),
}
GATE_NAMES = ("marketplace", "sourcing", "economics", "risk", "decision_readiness")
MONEY = Decimal("0.01")


class ProductValidationService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def create_project(self, data: dict[str, Any]) -> ProductValidationProject:
        product_id = uuid.UUID(str(data["product_id"]))
        product = self.db.get(ProductCandidate, product_id)
        if product is None:
            raise HTTPException(404, "Product not found")
        score = self._score(product_id, data.get("recommendation_snapshot_id"))
        existing = self.db.scalar(
            select(ProductValidationProject).where(
                ProductValidationProject.product_id == product_id,
                ProductValidationProject.source_recommendation_snapshot_id == score.id,
            )
        )
        if existing:
            return existing
        project = ProductValidationProject(
            product_id=product_id,
            source_discovery_run_id=self._uuid(data.get("source_discovery_run_id")),
            source_discovery_result_id=self._uuid(data.get("source_discovery_result_id")),
            source_recommendation_snapshot_id=score.id,
            title=data.get("title") or product.canonical_name,
            notes=data.get("notes"),
        )
        self.db.add(project)
        self.db.flush()
        self.create_packet(project, score)
        self.db.commit()
        self.db.refresh(project)
        return project

    def list_projects(self, status: str | None = None) -> list[ProductValidationProject]:
        query = (
            select(ProductValidationProject)
            .options(selectinload(ProductValidationProject.product))
            .order_by(ProductValidationProject.updated_at.desc())
        )
        if status:
            query = query.where(ProductValidationProject.status == status)
        return list(self.db.scalars(query))

    def get_project(self, project_id: uuid.UUID | str) -> ProductValidationProject:
        project = self.db.scalar(
            select(ProductValidationProject)
            .where(ProductValidationProject.id == self._uuid(project_id))
            .options(
                selectinload(ProductValidationProject.product),
                selectinload(ProductValidationProject.packets),
                selectinload(ProductValidationProject.transitions),
                selectinload(ProductValidationProject.poe_evidence),
                selectinload(ProductValidationProject.rfqs),
                selectinload(ProductValidationProject.quotes).selectinload(
                    ValidationSupplierQuote.supplier
                ),
                selectinload(ProductValidationProject.quotes).selectinload(
                    ValidationSupplierQuote.tiers
                ),
                selectinload(ProductValidationProject.gates),
            )
        )
        if project is None:
            raise HTTPException(404, "Validation project not found")
        return project

    def transition(
        self, project_id: uuid.UUID | str, to_status: str, reason: str, actor: str
    ) -> ProductValidationProject:
        project = self.get_project(project_id)
        if to_status not in TRANSITIONS.get(project.status, set()):
            allowed = sorted(TRANSITIONS.get(project.status, set()))
            raise HTTPException(
                409,
                f"Cannot transition from {project.status} to {to_status}. Allowed: {', '.join(allowed) or 'none'}",
            )
        if to_status == "approved_for_sample":
            latest = self.latest_gates(project.id)
            if latest.get("decision_readiness", {}).get("status") not in {"passed", "overridden"}:
                raise HTTPException(
                    409, "Decision readiness must pass or be overridden before sample approval"
                )
        old = project.status
        project.status = to_status
        project.completed_at = (
            datetime.now(UTC)
            if to_status in {"approved_for_sample", "rejected", "archived"}
            else None
        )
        self.db.add(
            ValidationTransition(
                validation_project_id=project.id,
                from_status=old,
                to_status=to_status,
                reason=reason,
                actor=actor,
            )
        )
        self.db.commit()
        self.db.expire_all()
        return project

    def create_packet(
        self, project: ProductValidationProject, score: OpportunityScore | None = None
    ) -> ValidationMarketplacePacket:
        score = score or self._score(
            project.product_id, str(project.source_recommendation_snapshot_id)
        )
        comparables = ComparableService(self.db).get_effective_comparables(
            project.product_id, sync=False
        )
        economics = ValidationService(self.db, self.settings).economics(project.product_id)
        evidence = ValidationService(self.db, self.settings).evidence_matrix(project.product_id)
        constraints = ValidationService(self.db, self.settings).latest_constraint(
            project.product_id
        )
        breakdown = score.score_breakdown or {}
        details = [
            {
                "asin": row.asin,
                "title": row.title,
                "brand": row.brand,
                "price": row.price,
                "price_observed_at": self._iso(row.price_observed_at),
                "sales_rank": (row.metadata_ or {}).get("bestseller_rank"),
                "rank_category": (row.metadata_ or {}).get("rank_category"),
                "rank_observed_at": self._iso(row.rank_observed_at),
                "review_count": (row.metadata_ or {}).get("review_count"),
                "rating": (row.metadata_ or {}).get("rating"),
                "fee_estimate": (row.metadata_ or {}).get("fee_estimate"),
                "fee_observed_at": self._iso(row.fee_observed_at),
                "fee_provenance": (row.metadata_ or {}).get("fee_provenance"),
                "relevance_status": row.relevance_status,
                "relevance_score": row.relevance_score,
            }
            for row in comparables
        ]
        version = (
            int(
                self.db.scalar(
                    select(func.coalesce(func.max(ValidationMarketplacePacket.version), 0)).where(
                        ValidationMarketplacePacket.validation_project_id == project.id
                    )
                )
                or 0
            )
            + 1
        )
        modeled = economics.get("modeled") or {}
        packet = ValidationMarketplacePacket(
            validation_project_id=project.id,
            version=version,
            recommendation_snapshot_id=score.id,
            scoring_version=score.scoring_version,
            opportunity_score=score.final_score,
            confidence_score=score.confidence_score,
            readiness_score=breakdown.get("data_readiness_score")
            or breakdown.get("readiness_score"),
            research_priority_score=breakdown.get("ranking_priority_score")
            or breakdown.get("research_priority_score"),
            expected_sale_price=self._decimal(economics.get("modeled_price")),
            amazon_fees_per_unit=self._decimal(economics.get("amazon_fees")),
            max_landed_cost=self._decimal(modeled.get("max_landed_cost")),
            effective_comparable_count=len(comparables),
            comparable_asins=[row.asin for row in comparables],
            comparable_details=details,
            demand_summary={"score": score.demand_score, "source": f"opportunity_score:{score.id}"},
            competition_summary={
                "score": score.competition_score,
                "source": f"opportunity_score:{score.id}",
            },
            economics_summary=jsonable_encoder({**economics, "source": "validation_service"}),
            risk_summary=jsonable_encoder({**constraints, "source": "constraint_evaluation"}),
            missing_evidence=evidence.get("missing_evidence", []),
            conflicting_evidence=[
                row["area"]
                for row in evidence.get("rows", [])
                if row.get("status") == "conflicting"
            ],
            observed_at=datetime.now(UTC),
        )
        self.db.add(packet)
        self.db.flush()
        return packet

    def refresh_packet(self, project_id: uuid.UUID | str) -> ValidationMarketplacePacket:
        project = self.get_project(project_id)
        result = AmazonRefreshPipeline(self.db).run_product(project.product_id)
        if result.status == "failed":
            raise HTTPException(502, f"Amazon refresh failed: {'; '.join(result.errors)}")
        score = ScoringService(self.db).score_product(project.product_id)
        packet = self.create_packet(project, score)
        self.db.commit()
        self.db.refresh(packet)
        return packet

    def upsert_poe(
        self, project_id: uuid.UUID | str, values: dict[str, Any]
    ) -> ValidationPoeEvidence:
        project = self.get_project(project_id)
        evidence = project.poe_evidence or ValidationPoeEvidence(validation_project_id=project.id)
        for key, value in values.items():
            setattr(evidence, key, value)
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def generate_rfq(self, project_id: uuid.UUID | str) -> ValidationRfq:
        project = self.get_project(project_id)
        packet = self.latest_packet(project.id)
        version = max((row.version for row in project.rfqs), default=0) + 1
        asins = packet.comparable_asins if packet else []
        spec = {
            key: "[TO BE CONFIRMED]"
            for key in (
                "concept_description",
                "target_customer",
                "dimensions",
                "materials",
                "colors_variants",
                "customization",
                "packaging",
                "labeling_barcode",
            )
        }
        questions = [
            "Sample cost",
            "MOQ",
            "Production lead time",
            "EXW price",
            "FOB price",
            "Tooling or mold fees",
            "Payment terms",
            "Quality-control process",
            "Factory audit and certification evidence",
        ]
        title = f"RFQ - {project.title}"
        markdown = self._render_rfq(title, project.title, asins, spec, [200, 500, 1000], questions)
        rfq = ValidationRfq(
            validation_project_id=project.id,
            version=version,
            title=title,
            product_specification=spec,
            requested_quantities=[200, 500, 1000],
            destination={"country": "[TO BE CONFIRMED]", "postal_code": "[TO BE CONFIRMED]"},
            required_certifications=["[TO BE CONFIRMED]"],
            questions=questions,
            rendered_markdown=markdown,
        )
        self.db.add(rfq)
        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    def revise_rfq(
        self, project_id: uuid.UUID | str, rfq_id: uuid.UUID | str, values: dict[str, Any]
    ) -> ValidationRfq:
        project = self.get_project(project_id)
        source = self.db.get(ValidationRfq, self._uuid(rfq_id))
        if source is None or source.validation_project_id != project.id:
            raise HTTPException(404, "RFQ not found")
        data = {
            "title": source.title,
            "product_specification": source.product_specification,
            "requested_quantities": source.requested_quantities,
            "destination": source.destination,
            "required_certifications": source.required_certifications,
            "questions": source.questions,
            "rendered_markdown": source.rendered_markdown,
        }
        data.update(values)
        revision = ValidationRfq(
            validation_project_id=project.id,
            version=max(row.version for row in project.rfqs) + 1,
            **data,
        )
        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def create_quote(
        self, project_id: uuid.UUID | str, values: dict[str, Any]
    ) -> ValidationSupplierQuote:
        project = self.get_project(project_id)
        supplier = self.db.get(Supplier, self._uuid(values.pop("supplier_id")))
        if supplier is None:
            raise HTTPException(404, "Supplier not found")
        tiers = values.pop("tiers", [])
        if values.get("rfq_id"):
            values["rfq_id"] = self._uuid(values["rfq_id"])
        quote = ValidationSupplierQuote(
            validation_project_id=project.id, supplier_id=supplier.id, **values
        )
        quote.currency = quote.currency.upper()
        quote.tiers = [SupplierQuoteTier(**tier) for tier in tiers]
        self.db.add(quote)
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def update_quote(
        self, project_id: uuid.UUID | str, quote_id: uuid.UUID | str, values: dict[str, Any]
    ) -> ValidationSupplierQuote:
        project = self.get_project(project_id)
        quote = self.db.get(ValidationSupplierQuote, self._uuid(quote_id))
        if quote is None or quote.validation_project_id != project.id:
            raise HTTPException(404, "Quote not found")
        tiers = values.pop("tiers", None)
        if values.get("rfq_id"):
            values["rfq_id"] = self._uuid(values["rfq_id"])
        for key, value in values.items():
            setattr(quote, key, value)
        if tiers is not None:
            quote.tiers.clear()
            quote.tiers.extend(SupplierQuoteTier(**tier) for tier in tiers)
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def tier_economics(
        self,
        project: ProductValidationProject,
        quote: ValidationSupplierQuote,
        tier: SupplierQuoteTier,
    ) -> dict[str, Any]:
        packet = self.latest_packet(project.id)
        price = packet.expected_sale_price if packet else None
        fees = packet.amazon_fees_per_unit if packet else None
        quantity = Decimal(tier.quantity)
        packaging = quote.packaging_cost_per_unit or Decimal(0)
        labeling = quote.labeling_cost_per_unit or Decimal(0)
        tooling = quote.tooling_cost or Decimal(0)
        parts = {
            "unit_product_cost": tier.unit_price,
            "unit_packaging_cost": packaging,
            "unit_labeling_cost": labeling,
            "unit_tooling_amortization": tooling / quantity,
        }
        for name in ("freight", "duty", "inspection", "prep", "miscellaneous"):
            parts[f"unit_{name}_cost"] = (getattr(tier, f"{name}_total") or Decimal(0)) / quantity
        landed = sum(parts.values(), Decimal(0)).quantize(MONEY, ROUND_HALF_UP)
        missing = []
        if price is None:
            missing.append("expected_sale_price")
        if fees is None:
            missing.append("amazon_fees_per_unit")
        ad_rate = Decimal(str(self.settings.validation_advertising_reserve_percent)) / 100
        return_rate = Decimal(str(self.settings.validation_returns_reserve_percent)) / 100
        target_rate = Decimal(str(self.settings.validation_target_margin_percent)) / 100
        other = Decimal(str(self.settings.validation_other_variable_cost_per_unit))
        contribution = margin = ceiling = None
        if not missing and price and fees is not None:
            ad = price * ad_rate
            returns = price * return_rate
            contribution = (price - fees - landed - ad - returns - other).quantize(
                MONEY, ROUND_HALF_UP
            )
            margin = (contribution / price * 100).quantize(MONEY, ROUND_HALF_UP)
            ceiling = (price - fees - price * target_rate - ad - returns - other).quantize(
                MONEY, ROUND_HALF_UP
            )
        return {
            **{key: float(value.quantize(MONEY, ROUND_HALF_UP)) for key, value in parts.items()},
            "landed_cost_per_unit": float(landed),
            "calculation_status": "incomplete" if missing else "complete",
            "missing_inputs": missing,
            "estimated_contribution_per_unit": float(contribution)
            if contribution is not None
            else None,
            "estimated_contribution_margin_percent": float(margin) if margin is not None else None,
            "max_landed_cost": float(ceiling) if ceiling is not None else None,
            "meets_cost_ceiling": bool(ceiling is not None and landed <= ceiling),
            "inputs": {
                "expected_sale_price": {
                    "value": float(price) if price is not None else None,
                    "source": f"validation_marketplace_packet_v{packet.version}"
                    if packet
                    else "missing",
                },
                "amazon_fees": {
                    "value": float(fees) if fees is not None else None,
                    "source": "validation_marketplace_packet",
                },
                "advertising_reserve_percent": {
                    "value": float(ad_rate * 100),
                    "source": "validation_config",
                },
                "returns_reserve_percent": {
                    "value": float(return_rate * 100),
                    "source": "validation_config",
                },
                "target_margin_percent": {
                    "value": float(target_rate * 100),
                    "source": "validation_config",
                },
            },
        }

    def evaluate_gates(self, project_id: uuid.UUID | str) -> dict[str, dict[str, Any]]:
        project = self.get_project(project_id)
        packet = self.latest_packet(project.id)
        now = datetime.now(UTC)
        gates: dict[str, dict[str, Any]] = {}
        missing = []
        if packet is None:
            missing.append("marketplace_packet")
        else:
            if (
                packet.effective_comparable_count
                < self.settings.validation_min_effective_comparables
            ):
                missing.append("effective_comparables")
            if packet.expected_sale_price is None:
                missing.append("price_evidence")
            if packet.amazon_fees_per_unit is None:
                missing.append("fee_evidence")
            if (packet.confidence_score or 0) < self.settings.validation_min_confidence:
                missing.append("confidence")
            observed_at = packet.observed_at
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=UTC)
            if observed_at < now - timedelta(
                days=self.settings.validation_marketplace_max_age_days
            ):
                missing.append("fresh_marketplace_evidence")
        gates["marketplace"] = self._gate(
            "marketplace",
            "passed" if not missing else "incomplete",
            "Marketplace evidence is sufficient."
            if not missing
            else "Marketplace evidence needs attention.",
            {"packet_version": packet.version if packet else None},
            missing,
            now,
        )
        received = [q for q in project.quotes if q.status in {"received", "shortlisted"}]
        complete_quote = any(
            q.moq
            and q.sample_cost is not None
            and q.production_lead_time_days is not None
            and q.tiers
            for q in received
        )
        sourcing_missing = []
        if len(received) < self.settings.validation_min_supplier_quotes:
            sourcing_missing.append("received_supplier_quotes")
        if not complete_quote:
            sourcing_missing.append("complete_supplier_quote")
        gates["sourcing"] = self._gate(
            "sourcing",
            "passed" if not sourcing_missing else "incomplete",
            f"{len(received)} received supplier quote(s).",
            {"received_quote_count": len(received)},
            sourcing_missing,
            now,
        )
        viable = []
        for quote in received:
            for tier in quote.tiers:
                calc = self.tier_economics(project, quote, tier)
                if (
                    calc["calculation_status"] == "complete"
                    and calc["meets_cost_ceiling"]
                    and (calc["estimated_contribution_margin_percent"] or 0)
                    >= self.settings.validation_target_margin_percent
                ):
                    viable.append({"quote_id": str(quote.id), "tier_id": str(tier.id)})
        econ_missing = (
            []
            if packet
            and packet.expected_sale_price is not None
            and packet.amazon_fees_per_unit is not None
            else ["marketplace_price_and_fees"]
        )
        econ_status = "passed" if viable else ("incomplete" if econ_missing else "failed")
        gates["economics"] = self._gate(
            "economics",
            econ_status,
            "A quote tier meets the target economics."
            if viable
            else "No quote tier currently meets target economics.",
            {"viable_tiers": viable},
            econ_missing,
            now,
        )
        constraint = self.db.scalar(
            select(ConstraintEvaluation)
            .where(ConstraintEvaluation.product_id == project.product_id)
            .order_by(ConstraintEvaluation.created_at.desc())
            .limit(1)
        )
        risk_missing = (
            []
            if constraint and constraint.evaluation_status == "completed"
            else ["completed_risk_evaluation"]
        )
        risk_status = (
            "incomplete"
            if risk_missing
            else ("passed" if constraint and constraint.eligible else "failed")
        )
        gates["risk"] = self._gate(
            "risk",
            risk_status,
            "Risk evaluation passed."
            if risk_status == "passed"
            else "Risk evaluation is incomplete or blocking.",
            {"constraint_evaluation_id": str(constraint.id) if constraint else None},
            risk_missing,
            now,
        )
        prior = self.latest_gates(project.id)
        component_status = {
            name: (
                prior.get(name, {}).get("status")
                if prior.get(name, {}).get("status") == "overridden"
                else gates[name]["status"]
            )
            for name in ("marketplace", "sourcing", "economics", "risk")
        }
        ready = all(status in {"passed", "overridden"} for status in component_status.values())
        gates["decision_readiness"] = self._gate(
            "decision_readiness",
            "passed" if ready else "incomplete",
            "Ready for a sample decision." if ready else "Resolve or override remaining gates.",
            {"component_status": component_status},
            [
                name
                for name, status in component_status.items()
                if status not in {"passed", "overridden"}
            ],
            now,
        )
        for result in gates.values():
            self.db.add(ValidationGateEvaluation(validation_project_id=project.id, **result))
        self.db.commit()
        return self.latest_gates(project.id)

    def override_gate(
        self, project_id: uuid.UUID | str, gate_name: str, reason: str, actor: str
    ) -> dict[str, Any]:
        if gate_name not in GATE_NAMES:
            raise HTTPException(404, "Unknown validation gate")
        project = self.get_project(project_id)
        latest = self.latest_gates(project.id).get(gate_name)
        if latest is None:
            raise HTTPException(409, "Evaluate gates before overriding one")
        row = ValidationGateEvaluation(
            validation_project_id=project.id,
            gate_name=gate_name,
            status="overridden",
            summary=f"Overridden by {actor}: {reason}",
            evidence=latest.get("evidence", {}),
            missing_inputs=latest.get("missing_inputs", []),
            rule_version=latest.get("rule_version", "validation_gates_v1"),
            override_reason=reason,
            override_actor=actor,
            evaluated_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.gate_dict(row)

    def latest_packet(self, project_id: uuid.UUID | str) -> ValidationMarketplacePacket | None:
        return self.db.scalar(
            select(ValidationMarketplacePacket)
            .where(ValidationMarketplacePacket.validation_project_id == self._uuid(project_id))
            .order_by(ValidationMarketplacePacket.version.desc())
            .limit(1)
        )

    def latest_gates(self, project_id: uuid.UUID | str) -> dict[str, dict[str, Any]]:
        rows = list(
            self.db.scalars(
                select(ValidationGateEvaluation)
                .where(ValidationGateEvaluation.validation_project_id == self._uuid(project_id))
                .order_by(
                    ValidationGateEvaluation.created_at.desc(), ValidationGateEvaluation.id.desc()
                )
            )
        )
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            result.setdefault(row.gate_name, self.gate_dict(row))
        return result

    def project_dict(
        self, project: ProductValidationProject, detail: bool = False
    ) -> dict[str, Any]:
        packet = self.latest_packet(project.id)
        gates = self.latest_gates(project.id)
        quotes = list(project.quotes) if hasattr(project, "quotes") else []
        tier_rows = [
            self.tier_economics(project, quote, tier) for quote in quotes for tier in quote.tiers
        ]
        base = {
            "id": str(project.id),
            "product_id": str(project.product_id),
            "product_name": project.product.canonical_name,
            "category": project.product.category,
            "source_discovery_run_id": str(project.source_discovery_run_id)
            if project.source_discovery_run_id
            else None,
            "source_discovery_result_id": str(project.source_discovery_result_id)
            if project.source_discovery_result_id
            else None,
            "source_recommendation_snapshot_id": str(project.source_recommendation_snapshot_id),
            "status": project.status,
            "title": project.title,
            "notes": project.notes,
            "latest_opportunity_score": packet.opportunity_score if packet else None,
            "confidence_score": packet.confidence_score if packet else None,
            "max_landed_cost": float(packet.max_landed_cost)
            if packet and packet.max_landed_cost is not None
            else None,
            "quote_count": len(quotes),
            "best_landed_cost": min(
                (row["landed_cost_per_unit"] for row in tier_rows), default=None
            ),
            "decision_readiness": gates.get("decision_readiness", {}).get(
                "status", "not_evaluated"
            ),
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "completed_at": project.completed_at,
        }
        if detail:
            base.update(
                {
                    "marketplace_packets": [
                        self.packet_dict(row)
                        for row in sorted(project.packets, key=lambda x: x.version, reverse=True)
                    ],
                    "poe_evidence": self.poe_dict(project.poe_evidence)
                    if project.poe_evidence
                    else None,
                    "rfqs": [
                        self.rfq_dict(row)
                        for row in sorted(project.rfqs, key=lambda x: x.version, reverse=True)
                    ],
                    "quotes": [self.quote_dict(project, row) for row in quotes],
                    "gates": gates,
                    "audit_history": [
                        self.transition_dict(row)
                        for row in sorted(
                            project.transitions, key=lambda x: x.created_at, reverse=True
                        )
                    ],
                }
            )
        return base

    def packet_dict(self, p: ValidationMarketplacePacket) -> dict[str, Any]:
        return {
            key: getattr(p, key)
            for key in (
                "version",
                "scoring_version",
                "opportunity_score",
                "confidence_score",
                "readiness_score",
                "research_priority_score",
                "effective_comparable_count",
                "comparable_asins",
                "comparable_details",
                "demand_summary",
                "competition_summary",
                "economics_summary",
                "risk_summary",
                "missing_evidence",
                "conflicting_evidence",
                "observed_at",
                "created_at",
            )
        } | {
            "id": str(p.id),
            "recommendation_snapshot_id": str(p.recommendation_snapshot_id),
            "expected_sale_price": float(p.expected_sale_price)
            if p.expected_sale_price is not None
            else None,
            "amazon_fees_per_unit": float(p.amazon_fees_per_unit)
            if p.amazon_fees_per_unit is not None
            else None,
            "max_landed_cost": float(p.max_landed_cost) if p.max_landed_cost is not None else None,
        }

    def quote_dict(
        self, project: ProductValidationProject, q: ValidationSupplierQuote
    ) -> dict[str, Any]:
        return {
            "id": str(q.id),
            "supplier_id": str(q.supplier_id),
            "supplier": {
                "id": str(q.supplier.id),
                "name": q.supplier.name,
                "platform": q.supplier.platform,
            },
            "rfq_id": str(q.rfq_id) if q.rfq_id else None,
            "currency": q.currency,
            "incoterm": q.incoterm,
            "moq": q.moq,
            "sample_cost": self._float(q.sample_cost),
            "tooling_cost": self._float(q.tooling_cost),
            "packaging_cost_per_unit": self._float(q.packaging_cost_per_unit),
            "labeling_cost_per_unit": self._float(q.labeling_cost_per_unit),
            "production_lead_time_days": q.production_lead_time_days,
            "sample_lead_time_days": q.sample_lead_time_days,
            "certification_notes": q.certification_notes,
            "payment_terms": q.payment_terms,
            "quote_valid_until": q.quote_valid_until,
            "status": q.status,
            "notes": q.notes,
            "manual_estimate_warning": "Manual estimate — verify before ordering",
            "tiers": [
                {
                    "id": str(t.id),
                    "quantity": t.quantity,
                    "unit_price": float(t.unit_price),
                    "freight_total": self._float(t.freight_total),
                    "duty_total": self._float(t.duty_total),
                    "inspection_total": self._float(t.inspection_total),
                    "prep_total": self._float(t.prep_total),
                    "miscellaneous_total": self._float(t.miscellaneous_total),
                    "economics": self.tier_economics(project, q, t),
                }
                for t in q.tiers
            ],
            "created_at": q.created_at,
            "updated_at": q.updated_at,
        }

    @staticmethod
    def gate_dict(g: ValidationGateEvaluation) -> dict[str, Any]:
        return {
            "id": str(g.id),
            "gate_name": g.gate_name,
            "status": g.status,
            "summary": g.summary,
            "evidence": g.evidence,
            "missing_inputs": g.missing_inputs,
            "evaluated_at": g.evaluated_at,
            "rule_version": g.rule_version,
            "override_reason": g.override_reason,
            "override_actor": g.override_actor,
        }

    @staticmethod
    def rfq_dict(r: ValidationRfq) -> dict[str, Any]:
        return {
            "id": str(r.id),
            "version": r.version,
            "title": r.title,
            "product_specification": r.product_specification,
            "requested_quantities": r.requested_quantities,
            "destination": r.destination,
            "required_certifications": r.required_certifications,
            "questions": r.questions,
            "rendered_markdown": r.rendered_markdown,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }

    @staticmethod
    def poe_dict(p: ValidationPoeEvidence) -> dict[str, Any]:
        return {
            key: (float(value) if isinstance(value, Decimal) else value)
            for key, value in {
                "id": str(p.id),
                "source_type": "manual_poe",
                "niche_name": p.niche_name,
                "reporting_period": p.reporting_period,
                "search_volume": p.search_volume,
                "search_volume_growth_percent": p.search_volume_growth_percent,
                "product_count": p.product_count,
                "average_price": p.average_price,
                "average_review_count": p.average_review_count,
                "conversion_rate_percent": p.conversion_rate_percent,
                "click_share_top_products_percent": p.click_share_top_products_percent,
                "unmet_demand_notes": p.unmet_demand_notes,
                "source_url": p.source_url,
                "observed_at": p.observed_at,
                "notes": p.notes,
                "entered_at": p.created_at,
                "updated_at": p.updated_at,
            }.items()
        }

    @staticmethod
    def transition_dict(t: ValidationTransition) -> dict[str, Any]:
        return {
            "id": str(t.id),
            "from_status": t.from_status,
            "to_status": t.to_status,
            "reason": t.reason,
            "actor": t.actor,
            "timestamp": t.created_at,
        }

    def _score(self, product_id: uuid.UUID, score_id: str | None) -> OpportunityScore:
        score = (
            self.db.get(OpportunityScore, self._uuid(score_id))
            if score_id
            else self.db.scalar(
                select(OpportunityScore)
                .where(OpportunityScore.product_id == product_id)
                .order_by(OpportunityScore.created_at.desc(), OpportunityScore.id.desc())
                .limit(1)
            )
        )
        if score is None or score.product_id != product_id:
            raise HTTPException(422, "A recommendation snapshot for this product is required")
        return score

    @staticmethod
    def _gate(
        name: str,
        status: str,
        summary: str,
        evidence: dict[str, Any],
        missing: list[str],
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "gate_name": name,
            "status": status,
            "summary": summary,
            "evidence": evidence,
            "missing_inputs": missing,
            "rule_version": "validation_gates_v1",
            "evaluated_at": now,
        }

    @staticmethod
    def _render_rfq(
        title: str,
        product: str,
        asins: list[str],
        spec: dict[str, str],
        quantities: list[int],
        questions: list[str],
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"**Product working name:** {product}",
            f"**Reference ASINs:** {', '.join(asins) or '[TO BE CONFIRMED]'}",
            "",
            "## Product specification",
        ]
        lines += [f"- **{key.replace('_', ' ').title()}:** {value}" for key, value in spec.items()]
        lines += [
            "",
            "## Requested quantities",
            *[f"- {q:,} units" for q in quantities],
            "",
            "## Destination",
            "- Country: [TO BE CONFIRMED]",
            "- Postal code: [TO BE CONFIRMED]",
            "",
            "## Supplier response requested",
            *[f"- {q}" for q in questions],
        ]
        return "\n".join(lines)

    @staticmethod
    def _uuid(value: Any) -> uuid.UUID | None:
        return uuid.UUID(str(value)) if value else None

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        return Decimal(str(value)).quantize(MONEY) if value is not None else None

    @staticmethod
    def _float(value: Decimal | None) -> float | None:
        return float(value) if value is not None else None

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None
