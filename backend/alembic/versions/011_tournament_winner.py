"""tournament winner: tournaments.winner_id

Revision ID: 011
Revises: 010
Create Date: 2026-09-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("winner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tournaments_winner_id_users", "tournaments", "users", ["winner_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_tournaments_winner_id_users", "tournaments", type_="foreignkey")
    op.drop_column("tournaments", "winner_id")
