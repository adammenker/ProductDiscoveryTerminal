from __future__ import annotations

import re
import string
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProductAlias, ProductCandidate, ProductStatus, RawObservation

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

    def normalize_new_observations(self) -> list[ProductCandidate]:
        observations = self.db.scalars(
            select(RawObservation)
            .where(RawObservation.product_id.is_(None))
            .order_by(RawObservation.created_at.asc())
        ).all()
        updated: dict[str, ProductCandidate] = {}
        alias_map = {
            alias.alias: product
            for alias, product in self.db.execute(
                select(ProductAlias, ProductCandidate).join(ProductCandidate)
            ).all()
        }

        for observation in observations:
            display_name = extract_product_name(observation)
            alias = normalize_alias(display_name)
            if not alias:
                continue

            product = self._find_product_for_alias(alias, alias_map)
            if product is None:
                product = ProductCandidate(
                    canonical_name=display_name,
                    category=_extract_category(observation),
                    status=ProductStatus.CANDIDATE,
                    description=_extract_description(observation),
                )
                self.db.add(product)
                self.db.flush()
                self.db.add(
                    ProductAlias(
                        product_id=product.id,
                        alias=alias,
                        source=observation.source,
                        confidence=1.0,
                    )
                )
                alias_map[alias] = product
            else:
                if product.category is None:
                    product.category = _extract_category(observation)
                if alias not in alias_map and not self._alias_exists(product.id, alias):
                    self.db.add(
                        ProductAlias(
                            product_id=product.id,
                            alias=alias,
                            source=observation.source,
                            confidence=0.9,
                        )
                    )
                alias_map[alias] = product

            observation.product_id = product.id
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
