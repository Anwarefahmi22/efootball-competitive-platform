"""group_knockout: groups table, tournaments.num_groups, participant/match group_id

Revision ID: 010
Revises: 009
Create Date: 2026-09-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tournament_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("tournaments", sa.Column("num_groups", sa.Integer(), nullable=True))
    op.add_column("tournament_participants", sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_participants_group_id_groups", "tournament_participants", "groups", ["group_id"], ["id"]
    )
    op.add_column("matches", sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_matches_group_id_groups", "matches", "groups", ["group_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_matches_group_id_groups", "matches", type_="foreignkey")
    op.drop_column("matches", "group_id")
    op.drop_constraint("fk_participants_group_id_groups", "tournament_participants", type_="foreignkey")
    op.drop_column("tournament_participants", "group_id")
    op.drop_column("tournaments", "num_groups")
    op.drop_table("groups")
