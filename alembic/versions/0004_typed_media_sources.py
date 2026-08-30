"""Make media source identities type-aware.

Revision ID: 0004_typed_media_sources
Revises: 0003_source_independent_genres
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_typed_media_sources"
down_revision: Union[str, Sequence[str], None] = "0003_source_independent_genres"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_sources", sa.Column("media_type", sa.String(length=20), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE media_sources ms
            SET media_type = m.type
            FROM media m
            WHERE m.id = ms.media_id
            """
        )
    )
    op.alter_column("media_sources", "media_type", nullable=False)
    op.drop_constraint("uq_media_source", "media_sources", type_="unique")
    op.create_unique_constraint(
        "uq_media_source",
        "media_sources",
        ["source", "source_id", "media_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_media_source", "media_sources", type_="unique")
    op.create_unique_constraint(
        "uq_media_source",
        "media_sources",
        ["source", "source_id"],
    )
    op.drop_column("media_sources", "media_type")
