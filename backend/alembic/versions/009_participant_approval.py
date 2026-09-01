"""participant approval: tournaments.requires_approval + participants.status

Revision ID: 009
Revises: 008
Create Date: 2026-09-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tournaments",
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tournament_participants",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="approved"),
    )


def downgrade() -> None:
    op.drop_column("tournament_participants", "status")
    op.drop_column("tournaments", "requires_approval")
