from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID

revision = "0004_v2_correctness_hardening"
down_revision = "0003_recommendation_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("comparable_asins", sa.Column("seed_category", sa.String(length=120), nullable=True))
    op.add_column("comparable_asins", sa.Column("amazon_category", sa.String(length=255), nullable=True))
    op.add_column("comparable_asins", sa.Column("amazon_product_type", sa.String(length=120), nullable=True))

    op.add_column("marketplace_asin_snapshots", sa.Column("snapshot_cohort_id", GUID(), nullable=True))
    op.add_column("marketplace_asin_snapshots", sa.Column("observation_fingerprint", sa.String(length=128), nullable=True))
    op.add_column("marketplace_asin_snapshots", sa.Column("rank_category", sa.String(length=255), nullable=True))
    op.add_column("marketplace_asin_snapshots", sa.Column("browse_node", sa.String(length=120), nullable=True))
    op.add_column("marketplace_asin_snapshots", sa.Column("rank_classification", sa.String(length=120), nullable=True))
    op.create_index(
        op.f("ix_marketplace_asin_snapshots_snapshot_cohort_id"),
        "marketplace_asin_snapshots",
        ["snapshot_cohort_id"],
    )
    op.create_index(
        op.f("ix_marketplace_asin_snapshots_observation_fingerprint"),
        "marketplace_asin_snapshots",
        ["observation_fingerprint"],
    )
    op.create_index(
        "ix_marketplace_asin_snapshots_product_cohort",
        "marketplace_asin_snapshots",
        ["product_id", "snapshot_cohort_id"],
    )
    op.create_unique_constraint(
        "uq_marketplace_snapshot_product_comparable_cohort",
        "marketplace_asin_snapshots",
        ["product_id", "comparable_asin_id", "snapshot_cohort_id"],
    )

    op.add_column(
        "constraint_evaluations",
        sa.Column("evaluation_status", sa.String(length=32), server_default="completed", nullable=False),
    )
    op.add_column(
        "constraint_evaluations",
        sa.Column("evaluation_version", sa.String(length=80), server_default="risk_rules_v1", nullable=False),
    )
    op.add_column("constraint_evaluations", sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE constraint_evaluations SET evaluated_at = created_at WHERE evaluated_at IS NULL")


def downgrade() -> None:
    op.drop_column("constraint_evaluations", "evaluated_at")
    op.drop_column("constraint_evaluations", "evaluation_version")
    op.drop_column("constraint_evaluations", "evaluation_status")

    op.drop_constraint(
        "uq_marketplace_snapshot_product_comparable_cohort",
        "marketplace_asin_snapshots",
        type_="unique",
    )
    op.drop_index("ix_marketplace_asin_snapshots_product_cohort", table_name="marketplace_asin_snapshots")
    op.drop_index(op.f("ix_marketplace_asin_snapshots_observation_fingerprint"), table_name="marketplace_asin_snapshots")
    op.drop_index(op.f("ix_marketplace_asin_snapshots_snapshot_cohort_id"), table_name="marketplace_asin_snapshots")
    op.drop_column("marketplace_asin_snapshots", "rank_classification")
    op.drop_column("marketplace_asin_snapshots", "browse_node")
    op.drop_column("marketplace_asin_snapshots", "rank_category")
    op.drop_column("marketplace_asin_snapshots", "observation_fingerprint")
    op.drop_column("marketplace_asin_snapshots", "snapshot_cohort_id")

    op.drop_column("comparable_asins", "amazon_product_type")
    op.drop_column("comparable_asins", "amazon_category")
    op.drop_column("comparable_asins", "seed_category")
