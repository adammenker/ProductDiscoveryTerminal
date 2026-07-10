from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID
from app.models.json import json_type

revision = "0002_validation_first"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplier_quotes",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("supplier_url", sa.String(length=1000), nullable=True),
        sa.Column("quote_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("freight_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("packaging_cost_per_unit", sa.Float(), nullable=True),
        sa.Column("moq", sa.Integer(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quote_status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_quotes_product_id"), "supplier_quotes", ["product_id"])

    op.create_table(
        "rule_profiles",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("hard_rules", json_type(), nullable=False),
        sa.Column("soft_rules", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_rule_profiles_is_default"), "rule_profiles", ["is_default"])

    op.create_table(
        "constraint_evaluations",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("rule_profile_id", GUID(), nullable=False),
        sa.Column("hard_failures", json_type(), nullable=False),
        sa.Column("soft_warnings", json_type(), nullable=False),
        sa.Column("risk_flags", json_type(), nullable=False),
        sa.Column("constraint_score", sa.Float(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_profile_id"], ["rule_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_constraint_evaluations_product_id"),
        "constraint_evaluations",
        ["product_id"],
    )
    op.create_index(
        op.f("ix_constraint_evaluations_rule_profile_id"),
        "constraint_evaluations",
        ["rule_profile_id"],
    )
    op.create_index(op.f("ix_constraint_evaluations_eligible"), "constraint_evaluations", ["eligible"])

    op.create_table(
        "opportunity_snapshots",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_reason", sa.String(length=255), nullable=False),
        sa.Column("discovery_source", sa.String(length=120), nullable=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(length=48), nullable=True),
        sa.Column("component_scores", json_type(), nullable=False),
        sa.Column("cost_ceiling", json_type(), nullable=False),
        sa.Column("supplier_validation", json_type(), nullable=False),
        sa.Column("constraint_evaluation", json_type(), nullable=False),
        sa.Column("evidence_matrix", json_type(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_opportunity_snapshots_product_id"),
        "opportunity_snapshots",
        ["product_id"],
    )

    op.create_table(
        "paper_trades",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("snapshot_id", GUID(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("entry_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_windows", json_type(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["opportunity_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_paper_trades_product_id"), "paper_trades", ["product_id"])
    op.create_index(op.f("ix_paper_trades_snapshot_id"), "paper_trades", ["snapshot_id"])
    op.create_index(op.f("ix_paper_trades_decision"), "paper_trades", ["decision"])
    op.create_index(op.f("ix_paper_trades_status"), "paper_trades", ["status"])

    op.create_table(
        "outcome_measurements",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("paper_trade_id", GUID(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_change", sa.Float(), nullable=True),
        sa.Column("review_count_change", sa.Float(), nullable=True),
        sa.Column("rank_change", sa.Float(), nullable=True),
        sa.Column("search_interest_change", sa.Float(), nullable=True),
        sa.Column("seller_count_change", sa.Float(), nullable=True),
        sa.Column("supplier_cost_change", sa.Float(), nullable=True),
        sa.Column("constraint_status_change", sa.String(length=120), nullable=True),
        sa.Column("outcome_label", sa.String(length=32), nullable=False),
        sa.Column("outcome_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["paper_trade_id"], ["paper_trades.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_outcome_measurements_paper_trade_id"),
        "outcome_measurements",
        ["paper_trade_id"],
    )
    op.create_index(
        op.f("ix_outcome_measurements_outcome_label"),
        "outcome_measurements",
        ["outcome_label"],
    )

    op.create_table(
        "backtest_runs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_days", sa.Integer(), nullable=True),
        sa.Column("filters", json_type(), nullable=False),
        sa.Column("metrics", json_type(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("backtest_runs")
    op.drop_table("outcome_measurements")
    op.drop_table("paper_trades")
    op.drop_table("opportunity_snapshots")
    op.drop_table("constraint_evaluations")
    op.drop_table("rule_profiles")
    op.drop_table("supplier_quotes")
