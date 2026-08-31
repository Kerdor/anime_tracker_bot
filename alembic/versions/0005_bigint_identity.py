"""Keep PostgreSQL bigint primary-key defaults created by the initial schema.

Revision ID: 0005_bigint_identity
Revises: 0004_typed_media_sources
Create Date: 2026-08-31

The initial migration already creates autoincrementing BIGINT primary keys on
PostgreSQL. PostgreSQL implements these columns with a sequence-backed default,
so attempting to add an IDENTITY to the same columns fails with
"column already has a default". The existing defaults are sufficient for
SQLAlchemy inserts and must be preserved.

"""
from typing import Sequence, Union


revision: str = "0005_bigint_identity"
down_revision: Union[str, Sequence[str], None] = "0004_typed_media_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
