"""AUD-10: server-side refresh-token sessions.

Revision ID: 021_refresh_sessions
Revises: 020_fk_indexes_pair_invite
Create Date: 2026-11-03

Creates refresh_sessions (see app.models.refresh_session). Rollout
note: refresh tokens issued before this migration carry no jti and
have no row here, so every existing session must log in once more
after the deploy that ships the AUD-10 code. Access tokens (30 min)
are unaffected. With the platform still pre-growth, that one-time
re-login is the accepted rollout cost — it is what converts an
irrevocable 7-day token into a revocable, rotating session.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "021_refresh_sessions"
down_revision = "020_fk_indexes_pair_invite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_sessions_family_id", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user_id", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
