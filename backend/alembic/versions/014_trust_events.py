"""auditable trust history

Revision ID: 014_trust_events
Revises: 013_global_standings
Create Date: 2026-09-14

Why this migration is genuinely required
----------------------------------------
`player_trust` (migration 004) stores only aggregate counters. With counters
alone the platform cannot answer the two questions an auditable moderation
system has to answer:

  1. WHY did this player's trust change?
  2. WHO made the administrative decision that changed it?

Neither is recoverable from the existing schema. `matches.disputed_by` records
who filed a dispute but nothing records who *resolved* it, and no column
anywhere stores a trust delta or the moment it was applied. Adding a column to
`player_trust` cannot help either: it is one row per player, so it can only
ever describe the most recent change.

This revision adds a single append-only `trust_events` table. Its unique
constraint on (user_id, event_type, match_id) is what makes
"one administrative event -> one trust consequence" a database guarantee
rather than an application-level boolean check, which is what the phase
requires for concurrent admin actions.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_trust_events"
down_revision: Union[str, None] = "013_global_standings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trust_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        # Delta applied and the resulting score, so a moderator can read the
        # history without replaying it.
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("trust_after", sa.Integer(), nullable=False),
        # Every trust event in this system is caused by a specific match, so
        # this is NOT NULL in practice — which is what makes the unique
        # constraint below an effective idempotency guard. (Postgres treats
        # NULLs as distinct, so a nullable column here would enforce nothing.)
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        # The admin who decided, for dispute resolution. NULL for events a
        # player triggered themselves.
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "event_type", "match_id", name="uq_trust_event_once_per_match"
        ),
    )
    op.create_index("ix_trust_events_user_created", "trust_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_trust_events_user_created", table_name="trust_events")
    op.drop_table("trust_events")
