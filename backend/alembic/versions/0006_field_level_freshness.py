from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_field_level_freshness"
down_revision = "0005_discovery_runs_eval"
branch_labels = None
depends_on = None

PROVENANCE_COLUMNS = (
    "catalog_observed_at",
    "price_observed_at",
    "offer_count_observed_at",
    "rank_observed_at",
    "fee_observed_at",
    "review_observed_at",
)


def upgrade() -> None:
    for table_name in ("comparable_asins", "marketplace_asin_snapshots"):
        for column_name in PROVENANCE_COLUMNS:
            op.add_column(
                table_name,
                sa.Column(column_name, sa.DateTime(timezone=True), nullable=True),
            )

    # Legacy rows only have aggregate freshness. Backfill only where the table
    # proves the corresponding value existed; otherwise provenance stays unknown.
    op.execute(
        "UPDATE comparable_asins SET catalog_observed_at = last_refreshed_at "
        "WHERE title IS NOT NULL"
    )
    op.execute(
        "UPDATE comparable_asins SET price_observed_at = last_refreshed_at "
        "WHERE price IS NOT NULL"
    )
    snapshot_backfills = {
        "price_observed_at": "price IS NOT NULL OR featured_offer_price IS NOT NULL OR lowest_offer_price IS NOT NULL",
        "offer_count_observed_at": "offer_count IS NOT NULL OR seller_count IS NOT NULL",
        "rank_observed_at": "bestseller_rank IS NOT NULL",
        "fee_observed_at": "fee_estimate IS NOT NULL OR fulfillment_fee IS NOT NULL OR referral_fee IS NOT NULL",
        "review_observed_at": "review_count IS NOT NULL OR rating IS NOT NULL",
    }
    for column_name, predicate in snapshot_backfills.items():
        op.execute(
            f"UPDATE marketplace_asin_snapshots SET {column_name} = observed_at "
            f"WHERE {predicate}"
        )


def downgrade() -> None:
    for table_name in ("marketplace_asin_snapshots", "comparable_asins"):
        for column_name in reversed(PROVENANCE_COLUMNS):
            op.drop_column(table_name, column_name)
