from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID
from app.models.json import json_type

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_candidates",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("subcategory", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("candidate", "active", "ignored", "archived", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_candidates_canonical_name"), "product_candidates", ["canonical_name"])
    op.create_index(op.f("ix_product_candidates_category"), "product_candidates", ["category"])
    op.create_index(op.f("ix_product_candidates_status"), "product_candidates", ["status"])

    op.create_table(
        "plugin_runs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("plugin_name", sa.String(length=120), nullable=False),
        sa.Column(
            "plugin_type",
            sa.Enum("ingestion", "analyzer", native_enum=False, length=24),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "success", "partial_success", "failed", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("parameters", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_runs_plugin_name"), "plugin_runs", ["plugin_name"])
    op.create_index(op.f("ix_plugin_runs_plugin_type"), "plugin_runs", ["plugin_type"])
    op.create_index(op.f("ix_plugin_runs_status"), "plugin_runs", ["status"])

    op.create_table(
        "product_aliases",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "alias", name="uq_product_alias"),
    )
    op.create_index(op.f("ix_product_aliases_product_id"), "product_aliases", ["product_id"])
    op.create_index("ix_product_aliases_alias", "product_aliases", ["alias"])

    op.create_table(
        "raw_observations",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("plugin_run_id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("source_plugin", sa.String(length=120), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum(
                "product",
                "review",
                "supplier",
                "trend",
                "social_post",
                "marketplace_listing",
                "search_result",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("metrics", json_type(), nullable=False),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("media_urls", json_type(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plugin_run_id"], ["plugin_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_raw_observations_content_hash"),
    )
    op.create_index(op.f("ix_raw_observations_content_hash"), "raw_observations", ["content_hash"])
    op.create_index(op.f("ix_raw_observations_entity_type"), "raw_observations", ["entity_type"])
    op.create_index(op.f("ix_raw_observations_plugin_run_id"), "raw_observations", ["plugin_run_id"])
    op.create_index(op.f("ix_raw_observations_product_id"), "raw_observations", ["product_id"])
    op.create_index(op.f("ix_raw_observations_source"), "raw_observations", ["source"])
    op.create_index("ix_raw_observations_source_entity", "raw_observations", ["source", "entity_type"])

    op.create_table(
        "market_signals",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column(
            "signal_type",
            sa.Enum(
                "search_volume",
                "search_growth",
                "bestseller_rank",
                "social_mentions",
                "review_count",
                "rating",
                "price",
                "seller_count",
                "trend_score",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_market_signals_product_id"), "market_signals", ["product_id"])
    op.create_index(op.f("ix_market_signals_signal_type"), "market_signals", ["signal_type"])

    op.create_table(
        "supplier_signals",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("supplier_url", sa.String(length=1000), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("moq", sa.Integer(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("shipping_estimate", sa.Float(), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_signals_product_id"), "supplier_signals", ["product_id"])

    op.create_table(
        "cost_models",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("selling_price", sa.Float(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("freight_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("packaging_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("fulfillment_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("marketplace_fee_per_unit", sa.Float(), nullable=True),
        sa.Column("storage_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("estimated_gross_margin", sa.Float(), nullable=True),
        sa.Column("estimated_net_margin", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("assumptions", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_models_product_id"), "cost_models", ["product_id"])

    op.create_table(
        "product_insights",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column(
            "insight_type",
            sa.Enum(
                "review_summary",
                "complaint_cluster",
                "feature_gap",
                "differentiation_idea",
                "risk_flag",
                "opportunity_thesis",
                "competition_summary",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_observation_ids", json_type(), nullable=False),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_insights_insight_type"), "product_insights", ["insight_type"])
    op.create_index(op.f("ix_product_insights_product_id"), "product_insights", ["product_id"])

    op.create_table(
        "opportunity_scores",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("scoring_version", sa.String(length=80), nullable=False),
        sa.Column("demand_score", sa.Float(), nullable=False),
        sa.Column("growth_score", sa.Float(), nullable=False),
        sa.Column("competition_score", sa.Float(), nullable=False),
        sa.Column("margin_score", sa.Float(), nullable=False),
        sa.Column("pain_point_score", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column(
            "recommendation",
            sa.Enum(
                "investigate",
                "watch",
                "skip",
                "strong_opportunity",
                "needs_more_data",
                native_enum=False,
                length=48,
            ),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("score_breakdown", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opportunity_scores_final_score"), "opportunity_scores", ["final_score"])
    op.create_index(op.f("ix_opportunity_scores_product_id"), "opportunity_scores", ["product_id"])
    op.create_index("ix_opportunity_scores_product_created", "opportunity_scores", ["product_id", "created_at"])
    op.create_index(op.f("ix_opportunity_scores_recommendation"), "opportunity_scores", ["recommendation"])


def downgrade() -> None:
    op.drop_table("opportunity_scores")
    op.drop_table("product_insights")
    op.drop_table("cost_models")
    op.drop_table("supplier_signals")
    op.drop_table("market_signals")
    op.drop_table("raw_observations")
    op.drop_table("product_aliases")
    op.drop_table("plugin_runs")
    op.drop_table("product_candidates")

