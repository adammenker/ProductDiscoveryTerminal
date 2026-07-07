from __future__ import annotations

from enum import StrEnum


class ProductStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    IGNORED = "ignored"
    ARCHIVED = "archived"


class ObservationEntityType(StrEnum):
    PRODUCT = "product"
    REVIEW = "review"
    SUPPLIER = "supplier"
    TREND = "trend"
    SOCIAL_POST = "social_post"
    MARKETPLACE_LISTING = "marketplace_listing"
    SEARCH_RESULT = "search_result"


class PluginType(StrEnum):
    INGESTION = "ingestion"
    ANALYZER = "analyzer"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class MarketSignalType(StrEnum):
    SEARCH_VOLUME = "search_volume"
    SEARCH_GROWTH = "search_growth"
    BESTSELLER_RANK = "bestseller_rank"
    SOCIAL_MENTIONS = "social_mentions"
    REVIEW_COUNT = "review_count"
    RATING = "rating"
    PRICE = "price"
    SELLER_COUNT = "seller_count"
    TREND_SCORE = "trend_score"


class InsightType(StrEnum):
    REVIEW_SUMMARY = "review_summary"
    COMPLAINT_CLUSTER = "complaint_cluster"
    FEATURE_GAP = "feature_gap"
    DIFFERENTIATION_IDEA = "differentiation_idea"
    RISK_FLAG = "risk_flag"
    OPPORTUNITY_THESIS = "opportunity_thesis"
    COMPETITION_SUMMARY = "competition_summary"


class Recommendation(StrEnum):
    INVESTIGATE = "investigate"
    WATCH = "watch"
    SKIP = "skip"
    STRONG_OPPORTUNITY = "strong_opportunity"
    NEEDS_MORE_DATA = "needs_more_data"

