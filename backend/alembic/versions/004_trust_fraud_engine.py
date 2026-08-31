"""trust/fraud engine: player_trust table + matches.disputed_by

Revision ID: 004
Revises: 003
Create Date: 2026-08-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("disputed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_matches_disputed_by_users", "matches", "users", ["disputed_by"], ["id"]
    )

    op.create_table(
        "player_trust",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("verified_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disputes_involved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("false_reports", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unjustified_disputes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("player_trust")
    op.drop_constraint("fk_matches_disputed_by_users", "matches", type_="foreignkey")
    op.drop_column("matches", "disputed_by")
