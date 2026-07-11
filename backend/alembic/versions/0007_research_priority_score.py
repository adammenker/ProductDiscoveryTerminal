from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_research_priority_score"
down_revision = "0006_field_level_freshness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discovery_run_results",
        sa.Column("evidence_confidence_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "discovery_run_results",
        sa.Column("ranking_priority_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discovery_run_results", "ranking_priority_score")
    op.drop_column("discovery_run_results", "evidence_confidence_score")
