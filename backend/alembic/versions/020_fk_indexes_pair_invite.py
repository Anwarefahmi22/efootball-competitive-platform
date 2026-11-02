"""Stage 2 remediation: foreign-key indexes + canonical pending-invite pair.

Revision ID: 020_fk_indexes_pair_invite
Revises: 019_invites_challenges
Create Date: 2026-11-03

AUD-04: the schema shipped with almost no indexes on foreign-key
columns, so hot lookups (tournament matches, participants, evidence,
inbox queries, likes/follows) degrade to sequential scans as volume
grows. This migration adds one plain index per hot FK column. Columns
already covered as the leading column of an existing unique index
(tournament_participants.tournament_id, player_likes.player_id,
post_likes.post_id, follows.follower_id, profiles.user_id,
player_ratings.user_id, challenge_matches.invite_id) are deliberately
NOT duplicated.

AUD-13: migration 019's pending-invite uniqueness covers the ORDERED
pair (challenger_id, opponent_id), so two simultaneous invites in
opposite directions could both insert. The index is rebuilt on the
canonical unordered pair (LEAST, GREATEST) so a pair of users can have
at most one pending match invite, in either direction. (LEAST/GREATEST
are defined for UUIDs in PostgreSQL.)

All indexes are plain btree; at the platform's current scale a regular
(non-concurrent) build inside the migration transaction is instant.
If the tables ever grow large, rebuild with CREATE INDEX CONCURRENTLY
outside a transaction instead.
"""
from alembic import op

revision = "020_fk_indexes_pair_invite"
down_revision = "019_invites_challenges"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_matches_tournament_id", "matches", "tournament_id"),
    ("ix_matches_player_a_id", "matches", "player_a_id"),
    ("ix_matches_player_b_id", "matches", "player_b_id"),
    ("ix_tournament_participants_user_id", "tournament_participants", "user_id"),
    ("ix_match_evidence_match_id", "match_evidence", "match_id"),
    ("ix_posts_author_id", "posts", "author_id"),
    ("ix_comments_post_id", "comments", "post_id"),
    ("ix_comments_author_id", "comments", "author_id"),
    ("ix_match_invites_challenger_id", "match_invites", "challenger_id"),
    ("ix_match_invites_opponent_id", "match_invites", "opponent_id"),
    ("ix_tournament_invites_tournament_id", "tournament_invites", "tournament_id"),
    ("ix_tournament_invites_invitee_id", "tournament_invites", "invitee_id"),
    ("ix_tournament_invites_inviter_id", "tournament_invites", "inviter_id"),
    ("ix_challenge_matches_player_a_id", "challenge_matches", "player_a_id"),
    ("ix_challenge_matches_player_b_id", "challenge_matches", "player_b_id"),
    ("ix_challenge_evidence_challenge_id", "challenge_evidence", "challenge_id"),
    ("ix_post_likes_user_id", "post_likes", "user_id"),
    ("ix_player_likes_user_id", "player_likes", "user_id"),
    ("ix_follows_followed_id", "follows", "followed_id"),
]


def upgrade() -> None:
    for name, table, column in INDEXES:
        op.create_index(name, table, [column])
    op.execute("DROP INDEX uq_match_invite_pending_pair")
    op.execute(
        "CREATE UNIQUE INDEX uq_match_invite_pending_pair ON match_invites "
        "(LEAST(challenger_id, opponent_id), GREATEST(challenger_id, opponent_id)) "
        "WHERE status = 'pending'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_match_invite_pending_pair")
    op.execute(
        "CREATE UNIQUE INDEX uq_match_invite_pending_pair ON match_invites "
        "(challenger_id, opponent_id) WHERE status = 'pending'"
    )
    for name, table, _column in reversed(INDEXES):
        op.drop_index(name, table_name=table)
