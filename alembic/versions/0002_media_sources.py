"""Move external media identity to MediaSource.

Revision ID: 0002_media_sources
Revises: 0001_initial
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_media_sources"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("media_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_id", name="uq_media_source"),
    )
    op.create_index("ix_media_sources_media_id", "media_sources", ["media_id"], unique=False)
    op.create_index("ix_media_sources_source", "media_sources", ["source"], unique=False)
    op.create_index("ix_media_sources_source_id", "media_sources", ["source_id"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO media_sources (media_id, source, source_id)
            SELECT id, 'mal', CAST(mal_id AS VARCHAR(100))
            FROM media
            WHERE mal_id IS NOT NULL
            """
        )
    )

    op.drop_index("ix_media_mal_id", table_name="media")
    op.drop_column("media", "mal_id")


def downgrade() -> None:
    op.add_column("media", sa.Column("mal_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE media
            SET mal_id = CAST(media_sources.source_id AS INTEGER)
            FROM media_sources
            WHERE media_sources.media_id = media.id
              AND media_sources.source = 'mal'
            """
        )
    )

    op.alter_column("media", "mal_id", nullable=False)
    op.create_unique_constraint("uq_media_mal_id", "media", ["mal_id"])
    op.create_index("ix_media_mal_id", "media", ["mal_id"], unique=False)

    op.drop_index("ix_media_sources_source_id", table_name="media_sources")
    op.drop_index("ix_media_sources_source", table_name="media_sources")
    op.drop_index("ix_media_sources_media_id", table_name="media_sources")
    op.drop_table("media_sources")
