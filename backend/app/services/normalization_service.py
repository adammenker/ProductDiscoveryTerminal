from __future__ import annotations

import re
import string
from collections.abc import Iterable
from datetime import UTC, datetime
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProductAlias, ProductCandidate, ProductStatus, RawObservation, SupplierQuote

STOP_WORDS = {
    "a",
    "an",
    "and",
    "best",
    "for",
    "new",
    "of",
    "pack",
    "style",
    "the",
    "with",
}


class NormalizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def normalize_new_observations(
        self,
        *,
        target_product_id: UUID | str | None = None,
        plugin_run_ids: Iterable[UUID | str] | None = None,
    ) -> list[ProductCandidate]:
        query = (
            select(RawObservation)
            .where(RawObservation.product_id.is_(None))
            .order_by(RawObservation.created_at.asc())
        )
        if plugin_run_ids is not None:
            run_ids = list(plugin_run_ids)
            if not run_ids:
                return []
            query = query.where(RawObservation.plugin_run_id.in_(run_ids))
        observations = self.db.scalars(query).all()
        updated: dict[str, ProductCandidate] = {}
        target_product = (
            self.db.get(ProductCandidate, target_product_id)
            if target_product_id is not None
            else None
        )
        target_alias = normalize_alias(target_product.canonical_name) if target_product else None
        alias_map = {
            alias.alias: product
            for alias, product in self.db.execute(
                select(ProductAlias, ProductCandidate).join(ProductCandidate)
            ).all()
        }
        asin_map = {
            asin: observation.product
            for observation in self.db.scalars(
                select(RawObservation).where(RawObservation.product_id.is_not(None))
            )
            if (asin := _observation_asin(observation)) and observation.product is not None
        }

        for observation in observations:
            display_name = extract_product_name(observation)
            alias = normalize_alias(display_name)
            if target_alias and alias != target_alias:
                alias = ""
            if not alias and target_product is None:
                continue

            asin = _observation_asin(observation)
            product = target_product
            if product is None:
                product = asin_map.get(asin) if asin else None
            if product is None and alias:
                product = self._find_product_for_alias(alias, alias_map)
            created_product = False
            if product is None and alias:
                product = ProductCandidate(
                    canonical_name=display_name,
                    category=_extract_category(observation),
                    status=ProductStatus.CANDIDATE,
                    description=_extract_description(observation),
                )
                self.db.add(product)
                self.db.flush()
                created_product = True
                self.db.add(
                    ProductAlias(
                        product_id=product.id,
                        alias=alias,
                        source=observation.source,
                        confidence=1.0,
                    )
                )
                alias_map[alias] = product
            if product is None:
                continue
            if not created_product:
                if product.category is None:
                    product.category = _extract_category(observation)
                if alias and alias not in alias_map and not self._alias_exists(product.id, alias):
                    self.db.add(
                        ProductAlias(
                            product_id=product.id,
                            alias=alias,
                            source=observation.source,
                            confidence=0.9,
                        )
                    )
                if alias:
                    alias_map[alias] = product

            observation.product_id = product.id
            product.updated_at = datetime.now(UTC)
            if asin:
                asin_map[asin] = product
            self._create_supplier_quote(product, observation)
            updated[str(product.id)] = product

        self.db.commit()
        return list(updated.values())

    def _find_product_for_alias(
        self,
        alias: str,
        alias_map: dict[str, ProductCandidate],
    ) -> ProductCandidate | None:
        exact = alias_map.get(alias)
        if exact is not None:
            return exact

        for existing_alias, product in alias_map.items():
            if SequenceMatcher(None, alias, existing_alias).ratio() >= 0.88:
                return product
        return None

    def _alias_exists(self, product_id, alias: str) -> bool:  # type: ignore[no-untyped-def]
        return (
            self.db.scalar(
                select(ProductAlias.id)
                .where(ProductAlias.product_id == product_id, ProductAlias.alias == alias)
                .limit(1)
            )
            is not None
        )

    def _create_supplier_quote(
        self,
        product: ProductCandidate,
        observation: RawObservation,
    ) -> None:
        unit_cost = (observation.metrics or {}).get("unit_cost")
        if unit_cost is None:
            return
        observation_id = str(observation.id)
        existing = self.db.scalars(
            select(SupplierQuote).where(SupplierQuote.product_id == product.id)
        ).all()
        if any((quote.metadata_ or {}).get("observation_id") == observation_id for quote in existing):
            return
        metadata = observation.metadata_ or {}
        freight = (observation.metrics or {}).get("freight_cost_per_unit")
        if freight is None:
            freight = (observation.metrics or {}).get("shipping_estimate")
        self.db.add(
            SupplierQuote(
                product_id=product.id,
                source=observation.source,
                supplier_name=metadata.get("supplier_name"),
                supplier_url=metadata.get("supplier_url"),
                unit_cost=float(unit_cost),
                freight_cost_per_unit=float(freight) if freight is not None else None,
                packaging_cost_per_unit=(
                    float(observation.metrics["packaging_cost_per_unit"])
                    if (observation.metrics or {}).get("packaging_cost_per_unit") is not None
                    else None
                ),
                moq=(
                    int(observation.metrics["moq"])
                    if (observation.metrics or {}).get("moq") is not None
                    else None
                ),
                lead_time_days=(
                    int(observation.metrics["lead_time_days"])
                    if (observation.metrics or {}).get("lead_time_days") is not None
                    else None
                ),
                country=metadata.get("country"),
                currency=metadata.get("currency") or "USD",
                quote_status="needs_review",
                confidence=0.65,
                notes=metadata.get("supplier_notes"),
                metadata_={"observation_id": observation_id, "imported_from": observation.source_plugin},
            )
        )


def extract_product_name(observation: RawObservation) -> str:
    metadata_name = (observation.metadata_ or {}).get("product_name")
    candidate = metadata_name or observation.title or observation.raw_text or "unknown product"
    candidate = str(candidate).strip().lower()
    candidate = re.split(r"\s[-|:]\s", candidate, maxsplit=1)[0]
    candidate = re.sub(r"\b(best seller|wholesale supplier estimate|trend signal)\b", "", candidate)
    candidate = " ".join(candidate.split())
    return candidate[:255]


def normalize_alias(value: str) -> str:
    value = value.lower()
    value = value.translate(str.maketrans("", "", string.punctuation))
    tokens = []
    for token in value.split():
        if token in STOP_WORDS:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return " ".join(tokens)


def _extract_category(observation: RawObservation) -> str | None:
    category = (observation.metadata_ or {}).get("category")
    return str(category).lower() if category else None


def _extract_description(observation: RawObservation) -> str | None:
    if observation.raw_text:
        return observation.raw_text[:500]
    return observation.title


def _observation_asin(observation: RawObservation) -> str | None:
    metadata = observation.metadata_ or {}
    value = metadata.get("asin") or metadata.get("comparable_asin")
    if not value and observation.external_id and "amazon" in observation.source.lower():
        value = observation.external_id.split(":", 1)[0]
    return str(value).upper() if value else None
