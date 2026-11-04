"""Presence tracking (migration 024).

Adds the three columns behind the activity-presence feature:

- ``users.last_seen_at`` — stamped by the client heartbeat while a
  logged-in page is actually visible.
- ``users.active_seconds`` — accumulated *real* activity: the server
  adds the gap between consecutive heartbeats only when that gap is
  small (<= 90 s), so an abandoned open tab never inflates it.
- ``users.presence_hidden`` — the player's own privacy switch; when
  on, their online state and last-seen are masked from everyone.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024_presence"
down_revision: Union[str, Sequence[str], None] = "023_email_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "active_seconds",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "presence_hidden",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "presence_hidden")
    op.drop_column("users", "active_seconds")
    op.drop_column("users", "last_seen_at")
