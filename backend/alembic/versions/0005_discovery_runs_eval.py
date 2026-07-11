from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID

revision = "0005_discovery_runs_eval"
down_revision = "0004_v2_correctness_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seed_lists",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "seed_keywords",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("seed_list_id", GUID(), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["seed_list_id"], ["seed_lists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seed_list_id", "keyword", name="uq_seed_keywords_list_keyword"),
    )
    op.create_index("ix_seed_keywords_keyword", "seed_keywords", ["keyword"])
    op.create_index("ix_seed_keywords_seed_list_id", "seed_keywords", ["seed_list_id"])
    op.create_index("ix_seed_keywords_status", "seed_keywords", ["status"])
    op.create_index("ix_seed_keywords_list_status", "seed_keywords", ["seed_list_id", "status"])

    op.create_table(
        "discovery_runs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("seed_list_id", GUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_plugins", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["seed_list_id"], ["seed_lists.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovery_runs_seed_list_id", "discovery_runs", ["seed_list_id"])
    op.create_index("ix_discovery_runs_status", "discovery_runs", ["status"])

    op.create_table(
        "candidate_clusters",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("discovery_run_id", GUID(), nullable=False),
        sa.Column("seed_keyword_id", GUID(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("normalized_key", sa.String(length=255), nullable=False),
        sa.Column("source_query", sa.String(length=255), nullable=False),
        sa.Column("representative_title", sa.String(length=500), nullable=True),
        sa.Column("evidence_observation_ids", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["discovery_run_id"], ["discovery_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seed_keyword_id"], ["seed_keywords.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "discovery_run_id",
            "seed_keyword_id",
            "normalized_key",
            name="uq_candidate_clusters_run_seed_key",
        ),
    )
    op.create_index("ix_candidate_clusters_discovery_run_id", "candidate_clusters", ["discovery_run_id"])
    op.create_index("ix_candidate_clusters_normalized_key", "candidate_clusters", ["normalized_key"])
    op.create_index("ix_candidate_clusters_run", "candidate_clusters", ["discovery_run_id"])
    op.create_index("ix_candidate_clusters_seed_keyword_id", "candidate_clusters", ["seed_keyword_id"])

    op.create_table(
        "discovery_run_results",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("discovery_run_id", GUID(), nullable=False),
        sa.Column("seed_keyword_id", GUID(), nullable=True),
        sa.Column("candidate_cluster_id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("score_snapshot_id", GUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=True),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(length=48), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_cluster_id"], ["candidate_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discovery_run_id"], ["discovery_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["score_snapshot_id"], ["opportunity_scores.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seed_keyword_id"], ["seed_keywords.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "discovery_run_id",
            "candidate_cluster_id",
            "product_id",
            name="uq_discovery_results_run_cluster_product",
        ),
    )
    op.create_index("ix_discovery_results_run_rank", "discovery_run_results", ["discovery_run_id", "rank_position"])
    op.create_index("ix_discovery_run_results_candidate_cluster_id", "discovery_run_results", ["candidate_cluster_id"])
    op.create_index("ix_discovery_run_results_discovery_run_id", "discovery_run_results", ["discovery_run_id"])
    op.create_index("ix_discovery_run_results_product_id", "discovery_run_results", ["product_id"])
    op.create_index("ix_discovery_run_results_score_snapshot_id", "discovery_run_results", ["score_snapshot_id"])
    op.create_index("ix_discovery_run_results_seed_keyword_id", "discovery_run_results", ["seed_keyword_id"])
    op.create_index("ix_discovery_run_results_status", "discovery_run_results", ["status"])

    op.create_table(
        "candidate_origins",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("product_id", GUID(), nullable=False),
        sa.Column("discovery_run_id", GUID(), nullable=False),
        sa.Column("seed_keyword_id", GUID(), nullable=True),
        sa.Column("candidate_cluster_id", GUID(), nullable=True),
        sa.Column("source_plugin", sa.String(length=120), nullable=False),
        sa.Column("source_query", sa.String(length=255), nullable=False),
        sa.Column("source_observation_id", GUID(), nullable=True),
        sa.Column("source_external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_cluster_id"], ["candidate_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["discovery_run_id"], ["discovery_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seed_keyword_id"], ["seed_keywords.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_observation_id"], ["raw_observations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "discovery_run_id",
            "seed_keyword_id",
            "product_id",
            "source_plugin",
            "source_external_id",
            name="uq_candidate_origins_source",
        ),
    )
    op.create_index("ix_candidate_origins_candidate_cluster_id", "candidate_origins", ["candidate_cluster_id"])
    op.create_index("ix_candidate_origins_discovery_run_id", "candidate_origins", ["discovery_run_id"])
    op.create_index("ix_candidate_origins_product", "candidate_origins", ["product_id"])
    op.create_index("ix_candidate_origins_product_id", "candidate_origins", ["product_id"])
    op.create_index("ix_candidate_origins_run_seed", "candidate_origins", ["discovery_run_id", "seed_keyword_id"])
    op.create_index("ix_candidate_origins_seed_keyword_id", "candidate_origins", ["seed_keyword_id"])
    op.create_index("ix_candidate_origins_source_observation_id", "candidate_origins", ["source_observation_id"])
    op.create_index("ix_candidate_origins_source_plugin", "candidate_origins", ["source_plugin"])


def downgrade() -> None:
    op.drop_index("ix_candidate_origins_source_plugin", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_source_observation_id", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_seed_keyword_id", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_run_seed", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_product_id", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_product", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_discovery_run_id", table_name="candidate_origins")
    op.drop_index("ix_candidate_origins_candidate_cluster_id", table_name="candidate_origins")
    op.drop_table("candidate_origins")

    op.drop_index("ix_discovery_run_results_status", table_name="discovery_run_results")
    op.drop_index("ix_discovery_run_results_seed_keyword_id", table_name="discovery_run_results")
    op.drop_index("ix_discovery_run_results_score_snapshot_id", table_name="discovery_run_results")
    op.drop_index("ix_discovery_run_results_product_id", table_name="discovery_run_results")
    op.drop_index("ix_discovery_run_results_discovery_run_id", table_name="discovery_run_results")
    op.drop_index("ix_discovery_run_results_candidate_cluster_id", table_name="discovery_run_results")
    op.drop_index("ix_discovery_results_run_rank", table_name="discovery_run_results")
    op.drop_table("discovery_run_results")

    op.drop_index("ix_candidate_clusters_seed_keyword_id", table_name="candidate_clusters")
    op.drop_index("ix_candidate_clusters_run", table_name="candidate_clusters")
    op.drop_index("ix_candidate_clusters_normalized_key", table_name="candidate_clusters")
    op.drop_index("ix_candidate_clusters_discovery_run_id", table_name="candidate_clusters")
    op.drop_table("candidate_clusters")

    op.drop_index("ix_discovery_runs_status", table_name="discovery_runs")
    op.drop_index("ix_discovery_runs_seed_list_id", table_name="discovery_runs")
    op.drop_table("discovery_runs")

    op.drop_index("ix_seed_keywords_list_status", table_name="seed_keywords")
    op.drop_index("ix_seed_keywords_status", table_name="seed_keywords")
    op.drop_index("ix_seed_keywords_seed_list_id", table_name="seed_keywords")
    op.drop_index("ix_seed_keywords_keyword", table_name="seed_keywords")
    op.drop_table("seed_keywords")

    op.drop_table("seed_lists")
