"""auth throttle counters

Revision ID: 016_auth_throttle
Revises: 015_media_files
Create Date: 2026-11-01

Why this migration exists
-------------------------
The 2026-11-01 audit found the auth endpoints accepted unlimited
attempts (password brute force + bot registrations). Serverless
functions share no memory, so the throttle counters live in a small
table: one row per key (login:email:*, login:ip:*, register:ip:*)
with a sliding window and a lock timestamp. See app.core.throttle.

On the production (Vercel) track this table was created with the
identical DDL through the Neon console before the code deploy, since
the /internal/migrate endpoint stays disabled there; this migration
keeps the schema history correct for every other track.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_auth_throttle"
down_revision: Union[str, None] = "015_media_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_throttle",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("auth_throttle")
