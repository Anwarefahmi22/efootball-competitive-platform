"""evidence images stored in DB (ephemeral-disk-proof hosting)

Revision ID: 012
Revises: 011
Create Date: 2026-09-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("match_evidence", sa.Column("image_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("match_evidence", "image_data")
