"""Create initial database schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=False)

    op.create_table(
        "media",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mal_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("title_original", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mal_id"),
    )
    op.create_index("ix_media_mal_id", "media", ["mal_id"], unique=False)
    op.create_index("ix_media_type", "media", ["type"], unique=False)

    op.create_table(
        "genres",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("mal_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mal_id"),
    )
    op.create_index("ix_genres_mal_id", "genres", ["mal_id"], unique=False)

    op.create_table(
        "user_media",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("media_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "media_id", name="uq_user_media"),
    )
    op.create_index("ix_user_media_user_id", "user_media", ["user_id"], unique=False)
    op.create_index("ix_user_media_media_id", "user_media", ["media_id"], unique=False)

    op.create_table(
        "media_genres",
        sa.Column("media_id", sa.BigInteger(), nullable=False),
        sa.Column("genre_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("media_id", "genre_id"),
        sa.UniqueConstraint("media_id", "genre_id", name="uq_media_genre"),
    )


def downgrade() -> None:
    op.drop_table("media_genres")
    op.drop_index("ix_user_media_media_id", table_name="user_media")
    op.drop_index("ix_user_media_user_id", table_name="user_media")
    op.drop_table("user_media")
    op.drop_index("ix_genres_mal_id", table_name="genres")
    op.drop_table("genres")
    op.drop_index("ix_media_type", table_name="media")
    op.drop_index("ix_media_mal_id", table_name="media")
    op.drop_table("media")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
