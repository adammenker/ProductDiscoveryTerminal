from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009_product_validation_pipeline"
down_revision = "0008_discovery_jsonb"
branch_labels = None
depends_on = None

GUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "product_validation_projects",
        sa.Column("id", GUID, primary_key=True),
        sa.Column("product_id", GUID, sa.ForeignKey("product_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_discovery_run_id", GUID, sa.ForeignKey("discovery_runs.id", ondelete="SET NULL")),
        sa.Column("source_discovery_result_id", GUID, sa.ForeignKey("discovery_run_results.id", ondelete="SET NULL")),
        sa.Column("source_recommendation_snapshot_id", GUID, sa.ForeignKey("opportunity_scores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "source_recommendation_snapshot_id", name="uq_validation_project_product_recommendation"),
    )
    op.create_index("ix_validation_projects_product_status", "product_validation_projects", ["product_id", "status"])
    op.create_index("ix_validation_projects_recommendation", "product_validation_projects", ["source_recommendation_snapshot_id"])
    op.create_table(
        "validation_transitions",
        sa.Column("id", GUID, primary_key=True), sa.Column("validation_project_id", GUID, sa.ForeignKey("product_validation_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=False), sa.Column("to_status", sa.String(32), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False, server_default="local_user"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_validation_transitions_validation_project_id", "validation_transitions", ["validation_project_id"])
    op.create_table(
        "validation_marketplace_packets",
        sa.Column("id", GUID, primary_key=True), sa.Column("validation_project_id", GUID, sa.ForeignKey("product_validation_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("recommendation_snapshot_id", GUID, sa.ForeignKey("opportunity_scores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scoring_version", sa.String(80), nullable=False), sa.Column("opportunity_score", sa.Float()), sa.Column("confidence_score", sa.Float()), sa.Column("readiness_score", sa.Float()), sa.Column("research_priority_score", sa.Float()),
        sa.Column("expected_sale_price", sa.Numeric(12, 2)), sa.Column("amazon_fees_per_unit", sa.Numeric(12, 2)), sa.Column("max_landed_cost", sa.Numeric(12, 2)),
        sa.Column("effective_comparable_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("comparable_asins", JSON, nullable=False, server_default="[]"), sa.Column("comparable_details", JSON, nullable=False, server_default="[]"),
        sa.Column("demand_summary", JSON, nullable=False, server_default="{}"), sa.Column("competition_summary", JSON, nullable=False, server_default="{}"), sa.Column("economics_summary", JSON, nullable=False, server_default="{}"), sa.Column("risk_summary", JSON, nullable=False, server_default="{}"),
        sa.Column("missing_evidence", JSON, nullable=False, server_default="[]"), sa.Column("conflicting_evidence", JSON, nullable=False, server_default="[]"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("validation_project_id", "version", name="uq_validation_packet_version"),
    )
    op.create_index("ix_validation_marketplace_packets_validation_project_id", "validation_marketplace_packets", ["validation_project_id"])
    op.create_table(
        "validation_poe_evidence", sa.Column("id", GUID, primary_key=True), sa.Column("validation_project_id", GUID, sa.ForeignKey("product_validation_projects.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("niche_name", sa.String(255)), sa.Column("reporting_period", sa.String(120)), sa.Column("search_volume", sa.Integer()), sa.Column("search_volume_growth_percent", sa.Numeric(8, 2)), sa.Column("product_count", sa.Integer()),
        sa.Column("average_price", sa.Numeric(12, 2)), sa.Column("average_review_count", sa.Numeric(12, 2)), sa.Column("conversion_rate_percent", sa.Numeric(8, 2)), sa.Column("click_share_top_products_percent", sa.Numeric(8, 2)),
        sa.Column("unmet_demand_notes", sa.Text()), sa.Column("source_url", sa.String(1000)), sa.Column("observed_at", sa.DateTime(timezone=True)), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "validation_rfqs", sa.Column("id", GUID, primary_key=True), sa.Column("validation_project_id", GUID, sa.ForeignKey("product_validation_projects.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("product_specification", JSON, nullable=False, server_default="{}"), sa.Column("requested_quantities", JSON, nullable=False, server_default="[200,500,1000]"), sa.Column("destination", JSON, nullable=False, server_default="{}"),
        sa.Column("required_certifications", JSON, nullable=False, server_default="[]"), sa.Column("questions", JSON, nullable=False, server_default="[]"), sa.Column("rendered_markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("validation_project_id", "version", name="uq_validation_rfq_version"),
    )
    op.create_index("ix_validation_rfqs_validation_project_id", "validation_rfqs", ["validation_project_id"])
    op.create_table(
        "suppliers", sa.Column("id", GUID, primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("platform", sa.String(32), nullable=False, server_default="other"), sa.Column("profile_url", sa.String(1000)), sa.Column("location", sa.String(255)),
        sa.Column("contact_name", sa.String(255)), sa.Column("contact_details", JSON), sa.Column("verified_status", sa.String(64)), sa.Column("years_in_business", sa.Integer()), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])
    op.create_table(
        "validation_supplier_quotes", sa.Column("id", GUID, primary_key=True), sa.Column("validation_project_id", GUID, sa.ForeignKey("product_validation_projects.id", ondelete="CASCADE"), nullable=False), sa.Column("supplier_id", GUID, sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False), sa.Column("rfq_id", GUID, sa.ForeignKey("validation_rfqs.id", ondelete="SET NULL")),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"), sa.Column("incoterm", sa.String(32)), sa.Column("moq", sa.Integer()), sa.Column("sample_cost", sa.Numeric(12, 2)), sa.Column("tooling_cost", sa.Numeric(12, 2)), sa.Column("packaging_cost_per_unit", sa.Numeric(12, 2)), sa.Column("labeling_cost_per_unit", sa.Numeric(12, 2)),
        sa.Column("production_lead_time_days", sa.Integer()), sa.Column("sample_lead_time_days", sa.Integer()), sa.Column("certification_notes", sa.Text()), sa.Column("payment_terms", sa.Text()), sa.Column("quote_valid_until", sa.Date()), sa.Column("status", sa.String(32), nullable=False, server_default="draft"), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_validation_supplier_quotes_validation_project_id", "validation_supplier_quotes", ["validation_project_id"])
    op.create_index("ix_validation_supplier_quotes_supplier_id", "validation_supplier_quotes", ["supplier_id"])
    op.create_index("ix_validation_supplier_quotes_status", "validation_supplier_quotes", ["status"])
    op.create_table(
        "supplier_quote_tiers", sa.Column("id", GUID, primary_key=True), sa.Column("supplier_quote_id", GUID, sa.ForeignKey("validation_supplier_quotes.id", ondelete="CASCADE"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("freight_total", sa.Numeric(12, 2)), sa.Column("duty_total", sa.Numeric(12, 2)), sa.Column("inspection_total", sa.Numeric(12, 2)), sa.Column("prep_total", sa.Numeric(12, 2)), sa.Column("miscellaneous_total", sa.Numeric(12, 2)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("supplier_quote_id", "quantity", name="uq_supplier_quote_tier_quantity"),
    )
    op.create_index("ix_supplier_quote_tiers_supplier_quote_id", "supplier_quote_tiers", ["supplier_quote_id"])
    op.create_table(
        "validation_gate_evaluations", sa.Column("id", GUID, primary_key=True), sa.Column("validation_project_id", GUID, sa.ForeignKey("product_validation_projects.id", ondelete="CASCADE"), nullable=False), sa.Column("gate_name", sa.String(32), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", JSON, nullable=False, server_default="{}"), sa.Column("missing_inputs", JSON, nullable=False, server_default="[]"), sa.Column("rule_version", sa.String(80), nullable=False, server_default="validation_gates_v1"), sa.Column("override_reason", sa.Text()), sa.Column("override_actor", sa.String(120)), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_validation_gate_project_name_created", "validation_gate_evaluations", ["validation_project_id", "gate_name", "created_at"])


def downgrade() -> None:
    for table in ["validation_gate_evaluations", "supplier_quote_tiers", "validation_supplier_quotes", "suppliers", "validation_rfqs", "validation_poe_evidence", "validation_marketplace_packets", "validation_transitions", "product_validation_projects"]:
        op.drop_table(table)
