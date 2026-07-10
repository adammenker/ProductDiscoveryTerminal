from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PluginRun, ProductCandidate, RawObservation, RunStatus
from app.pipeline.analyzer_runner import AnalyzerRunner
from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import (
    IngestionQuery,
    PipelineRunRequest,
    PipelineRunResponse,
    PluginRunSummary,
)
from app.services.scoring_service import ScoringService


class AmazonRefreshPipeline:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def run(self, limit: int = 10) -> PipelineRunResponse:
        products = list(
            self.db.scalars(
                select(ProductCandidate)
                .order_by(ProductCandidate.updated_at.desc())
                .limit(max(1, min(limit, 20)))
            )
        )
        if not products:
            return PipelineRunResponse(
                status=RunStatus.SUCCESS.value,
                plugin_runs=[],
                products_updated=0,
                scores_updated=0,
                observations_created=0,
                errors=[],
                message="No existing candidates to refresh. Create a candidate in Validator first, then run Amazon research.",
            )

        runner = PipelineRunner(self.db)
        summaries: list[PluginRunSummary] = []
        errors: list[str] = []
        observations_created = 0
        product_ids: list[UUID | str] = [str(product.id) for product in products]

        for product in products:
            catalog_limit = max(1, min(int(self.settings.amazon_refresh_catalog_limit), 20))
            pricing_limit = max(1, min(int(self.settings.amazon_refresh_pricing_limit), 20))
            catalog = runner.run(
                PipelineRunRequest(
                    plugins=["amazon_catalog_spapi"],
                    query=IngestionQuery(
                        query=product.canonical_name,
                        category=product.category,
                        limit=catalog_limit,
                        metadata={"product_id": str(product.id)},
                    ),
                    run_analyzers=False,
                    score=False,
                )
            )
            observations_created += catalog.observations_created
            summaries.extend(catalog.plugin_runs)
            errors.extend(catalog.errors)

            asins = self._asins(product.id)
            if not asins:
                errors.append(f"{product.canonical_name}: Amazon Catalog returned no comparable ASINs.")
                continue

            pricing = runner.run(
                PipelineRunRequest(
                    plugins=["amazon_pricing_spapi"],
                    query=IngestionQuery(
                        query=product.canonical_name,
                        category=product.category,
                        limit=pricing_limit,
                        metadata={"product_id": str(product.id), "asins": asins},
                    ),
                    run_analyzers=False,
                    score=False,
                )
            )
            observations_created += pricing.observations_created
            summaries.extend(pricing.plugin_runs)
            errors.extend(pricing.errors)

            fee_inputs = self._fee_inputs(product.id, asins)
            if fee_inputs:
                fees = runner.run(
                    PipelineRunRequest(
                        plugins=["amazon_fees_spapi"],
                        query=IngestionQuery(
                            query=product.canonical_name,
                            category=product.category,
                            limit=len(fee_inputs),
                            metadata={
                                "product_id": str(product.id),
                                "asins": fee_inputs,
                            },
                        ),
                        run_analyzers=False,
                        score=False,
                    )
                )
                observations_created += fees.observations_created
                summaries.extend(fees.plugin_runs)
                errors.extend(fees.errors)

        analyzer_runs = AnalyzerRunner(self.db).run(product_ids)
        summaries.extend(_run_summary(run) for run in analyzer_runs)
        errors.extend(
            f"{run.plugin_name}: {run.error_message}"
            for run in analyzer_runs
            if run.error_message
        )
        scores = ScoringService(self.db).score_products(product_ids)
        failed = any(
            summary.status in {RunStatus.FAILED.value, RunStatus.PARTIAL_SUCCESS.value}
            for summary in summaries
        )
        return PipelineRunResponse(
            status=RunStatus.PARTIAL_SUCCESS.value if failed or errors else RunStatus.SUCCESS.value,
            plugin_runs=summaries,
            products_updated=len(product_ids),
            scores_updated=len(scores),
            observations_created=observations_created,
            errors=errors,
        )

    def _asins(self, product_id: Any) -> list[str]:
        asins = []
        for observation in self.db.scalars(
            select(RawObservation)
            .where(
                RawObservation.product_id == product_id,
                RawObservation.source == "amazon_sp_api",
            )
            .order_by(RawObservation.observed_at.desc())
        ):
            metadata = observation.metadata_ or {}
            value = metadata.get("asin") or metadata.get("comparable_asin")
            if not value and observation.external_id:
                value = observation.external_id.split(":", 1)[0]
            asin = str(value).upper().split(":", 1)[0] if value else ""
            if len(asin) == 10 and asin not in asins:
                asins.append(asin)
        return asins[:10]

    def _fee_inputs(self, product_id: Any, asins: list[str]) -> list[dict[str, Any]]:
        prices: dict[str, float] = {}
        for observation in self.db.scalars(
            select(RawObservation)
            .where(
                RawObservation.product_id == product_id,
                RawObservation.source_plugin == "amazon_pricing_spapi",
            )
            .order_by(RawObservation.observed_at.desc())
        ):
            asin = str((observation.metadata_ or {}).get("asin") or "").upper()
            price = (observation.metrics or {}).get("price")
            if asin and price is not None and asin not in prices:
                prices[asin] = float(price)

        fresh_fees = self._fresh_fee_prices(product_id)
        limit = max(0, min(int(self.settings.amazon_refresh_fee_limit), len(asins)))
        inputs: list[dict[str, Any]] = []
        for asin in asins:
            modeled_price = round(float(prices.get(asin, 24.99)), 2)
            if any(abs(existing_price - modeled_price) <= 0.01 for existing_price in fresh_fees.get(asin, [])):
                continue
            inputs.append({"asin": asin, "modeled_price": modeled_price})
            if len(inputs) >= limit:
                break
        return inputs

    def _fresh_fee_prices(self, product_id: Any) -> dict[str, list[float]]:
        cutoff = datetime.now(UTC) - timedelta(
            hours=max(0.0, float(self.settings.amazon_fees_cache_ttl_hours))
        )
        prices: dict[str, list[float]] = {}
        for observation in self.db.scalars(
            select(RawObservation)
            .where(
                RawObservation.product_id == product_id,
                RawObservation.source_plugin == "amazon_fees_spapi",
                RawObservation.observed_at >= cutoff,
            )
            .order_by(RawObservation.observed_at.desc())
        ):
            asin = str((observation.metadata_ or {}).get("asin") or "").upper()
            selling_price = (observation.metrics or {}).get("selling_price")
            if not asin or selling_price is None:
                continue
            try:
                prices.setdefault(asin, []).append(round(float(selling_price), 2))
            except (TypeError, ValueError):
                continue
        return prices


def _run_summary(run: PluginRun) -> PluginRunSummary:
    return PluginRunSummary(
        id=str(run.id),
        plugin_name=run.plugin_name,
        plugin_type=run.plugin_type.value,
        status=run.status.value,
        records_created=run.records_created,
        records_updated=run.records_updated,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at or datetime.now(UTC),
    )
