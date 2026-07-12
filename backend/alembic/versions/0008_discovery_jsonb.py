from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_discovery_jsonb"
down_revision = "0007_research_priority_score"
branch_labels = None
depends_on = None

JSON_COLUMNS = {
    "seed_lists": ("metadata",),
    "seed_keywords": ("metadata",),
    "discovery_runs": ("source_plugins", "parameters", "summary"),
    "candidate_clusters": ("evidence_observation_ids", "metadata"),
    "candidate_origins": ("metadata",),
    "discovery_run_results": ("metadata",),
}


def upgrade() -> None:
    for table_name, column_names in JSON_COLUMNS.items():
        for column_name in column_names:
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.JSON(),
                type_=postgresql.JSONB(astext_type=sa.Text()),
                postgresql_using=f"{column_name}::jsonb",
                existing_nullable=False,
            )


def downgrade() -> None:
    for table_name, column_names in reversed(JSON_COLUMNS.items()):
        for column_name in reversed(column_names):
            op.alter_column(
                table_name,
                column_name,
                existing_type=postgresql.JSONB(astext_type=sa.Text()),
                type_=sa.JSON(),
                postgresql_using=f"{column_name}::json",
                existing_nullable=False,
            )
