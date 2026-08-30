"""Make genres independent from MAL.

Revision ID: 0003_source_independent_genres
Revises: 0002_media_sources
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_source_independent_genres"
down_revision: Union[str, Sequence[str], None] = "0002_media_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("genres", sa.Column("name_new", sa.String(length=100), nullable=True))
    op.execute(sa.text("UPDATE genres SET name_new = name"))

    op.execute(
        sa.text(
            """
            DELETE FROM media_genres mg
            USING genres duplicate, genres keeper
            WHERE mg.genre_id = duplicate.id
              AND duplicate.name_new = keeper.name_new
              AND duplicate.id > keeper.id
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE media_genres mg
            SET genre_id = keeper.id
            FROM genres duplicate
            JOIN genres keeper ON keeper.name_new = duplicate.name_new
            WHERE mg.genre_id = duplicate.id
              AND duplicate.id > keeper.id
            """
        )
    )

    op.drop_column("genres", "mal_id")
    op.drop_index("ix_genres_mal_id", table_name="genres")
    op.drop_column("genres", "name")
    op.alter_column("genres", "name_new", new_column_name="name", nullable=False)
    op.create_unique_constraint("uq_genre_name", "genres", ["name"])


def downgrade() -> None:
    op.drop_constraint("uq_genre_name", "genres", type_="unique")
    op.add_column("genres", sa.Column("mal_id", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE genres SET mal_id = id"))
    op.alter_column("genres", "mal_id", nullable=False)
    op.create_unique_constraint("genres_mal_id_key", "genres", ["mal_id"])
    op.create_index("ix_genres_mal_id", "genres", ["mal_id"], unique=False)
