"""Phase 2: invites, challenge matches, challenge evidence.

Revision ID: 019_invites_challenges
Revises: 018_squad_image
Create Date: 2026-11-02

Adds match_invites / tournament_invites / challenge_matches /
challenge_evidence, one-live-pending-invite partial unique indexes, and
drops the trust_events.match_id foreign key so trust consequences can be
recorded for challenge matches too (the column stays a plain UUID
reference; ids from either table are unique in practice). On the Vercel
track this DDL is applied through the Neon console before the code
deploy, the same way 017/018 were.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "019_invites_challenges"
down_revision = "018_squad_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "challenge_matches",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("invite_id", PGUUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("player_a_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("player_b_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="ready"),
        sa.Column("score_a", sa.Integer(), nullable=True),
        sa.Column("score_b", sa.Integer(), nullable=True),
        sa.Column("winner_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("disputed_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "match_invites",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("challenger_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opponent_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("challenge_id", PGUUID(as_uuid=True), sa.ForeignKey("challenge_matches.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "tournament_invites",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tournament_id", PGUUID(as_uuid=True), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inviter_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invitee_id", PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "challenge_evidence",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("challenge_id", PGUUID(as_uuid=True), sa.ForeignKey("challenge_matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_by", PGUUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("claimed_score_a", sa.Integer(), nullable=False),
        sa.Column("claimed_score_b", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(500), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_match_invite_pending_pair ON match_invites (challenger_id, opponent_id) WHERE status = 'pending'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_tournament_invite_pending ON tournament_invites (tournament_id, invitee_id) WHERE status = 'pending'"
    )
    op.drop_constraint("trust_events_match_id_fkey", "trust_events", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key(
        "trust_events_match_id_fkey", "trust_events", "matches", ["match_id"], ["id"], ondelete="CASCADE"
    )
    op.execute("DROP INDEX IF EXISTS uq_tournament_invite_pending")
    op.execute("DROP INDEX IF EXISTS uq_match_invite_pending_pair")
    op.drop_table("challenge_evidence")
    op.drop_table("tournament_invites")
    op.drop_table("match_invites")
    op.drop_table("challenge_matches")
