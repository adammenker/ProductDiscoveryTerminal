from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID
from app.models.json import json_type

revision = "0003_recommendation_v2"
down_revision = "0002_validation_first"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comparable_asins",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("product_type", sa.String(length=120), nullable=True),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("dimensions", json_type(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("relevance_status", sa.String(length=64), nullable=False),
        sa.Column("relevance_reasons", json_type(), nullable=False),
        sa.Column("automatic_relevance_version", sa.String(length=80), nullable=False),
        sa.Column("manually_overridden", sa.Boolean(), nullable=False),
        sa.Column("manual_override_reason", sa.Text(), nullable=True),
        sa.Column("discovered_from_query", sa.String(length=255), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "asin", name="uq_comparable_asins_product_asin"),
    )
    op.create_index(op.f("ix_comparable_asins_asin"), "comparable_asins", ["asin"])
    op.create_index(op.f("ix_comparable_asins_product_id"), "comparable_asins", ["product_id"])
    op.create_index(
        "ix_comparable_asins_product_status",
        "comparable_asins",
        ["product_id", "relevance_status"],
    )
    op.create_index(
        op.f("ix_comparable_asins_relevance_status"),
        "comparable_asins",
        ["relevance_status"],
    )

    op.create_table(
        "marketplace_asin_snapshots",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("comparable_asin_id", GUID(), nullable=True),
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("featured_offer_price", sa.Float(), nullable=True),
        sa.Column("lowest_offer_price", sa.Float(), nullable=True),
        sa.Column("offer_count", sa.Float(), nullable=True),
        sa.Column("seller_count", sa.Float(), nullable=True),
        sa.Column("bestseller_rank", sa.Float(), nullable=True),
        sa.Column("bestseller_category", sa.String(length=255), nullable=True),
        sa.Column("review_count", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("fee_estimate", sa.Float(), nullable=True),
        sa.Column("fulfillment_fee", sa.Float(), nullable=True),
        sa.Column("referral_fee", sa.Float(), nullable=True),
        sa.Column("source_observation_ids", json_type(), nullable=False),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["comparable_asin_id"], ["comparable_asins.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketplace_asin_snapshots_asin"),
        "marketplace_asin_snapshots",
        ["asin"],
    )
    op.create_index(
        "ix_marketplace_asin_snapshots_asin_observed",
        "marketplace_asin_snapshots",
        ["asin", "observed_at"],
    )
    op.create_index(
        op.f("ix_marketplace_asin_snapshots_comparable_asin_id"),
        "marketplace_asin_snapshots",
        ["comparable_asin_id"],
    )
    op.create_index(
        "ix_marketplace_asin_snapshots_product_observed",
        "marketplace_asin_snapshots",
        ["product_id", "observed_at"],
    )
    op.create_index(
        op.f("ix_marketplace_asin_snapshots_product_id"),
        "marketplace_asin_snapshots",
        ["product_id"],
    )

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("recommendation_snapshot_id", GUID(), nullable=True),
        sa.Column("verdict", sa.String(length=64), nullable=False),
        sa.Column("reasons", json_type(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_snapshot_id"],
            ["opportunity_scores.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendation_feedback_product_id"), "recommendation_feedback", ["product_id"])
    op.create_index(
        op.f("ix_recommendation_feedback_recommendation_snapshot_id"),
        "recommendation_feedback",
        ["recommendation_snapshot_id"],
    )
    op.create_index(op.f("ix_recommendation_feedback_verdict"), "recommendation_feedback", ["verdict"])


def downgrade() -> None:
    op.drop_table("recommendation_feedback")
    op.drop_table("marketplace_asin_snapshots")
    op.drop_table("comparable_asins")
