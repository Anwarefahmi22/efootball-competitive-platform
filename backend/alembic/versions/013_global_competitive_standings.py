"""add global competitive points and goal statistics

Revision ID: 013
Revises: 012
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_global_standings"
down_revision: Union[str, None] = "013_free_competition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("player_ratings", sa.Column("draws", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("player_ratings", sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("player_ratings", sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("player_ratings", sa.Column("points", sa.Integer(), nullable=False, server_default="0"))
    op.execute(
        sa.text(
            """
            UPDATE player_ratings AS pr
            SET
                draws = COALESCE((
                    SELECT COUNT(*)
                    FROM matches AS m
                    WHERE m.status = 'completed'
                      AND (m.player_a_id = pr.user_id OR m.player_b_id = pr.user_id)
                      AND m.score_a = m.score_b
                ), 0),
                goals_for = COALESCE((
                    SELECT SUM(CASE WHEN m.player_a_id = pr.user_id THEN m.score_a ELSE m.score_b END)
                    FROM matches AS m
                    WHERE m.status = 'completed'
                      AND (m.player_a_id = pr.user_id OR m.player_b_id = pr.user_id)
                ), 0),
                goals_against = COALESCE((
                    SELECT SUM(CASE WHEN m.player_a_id = pr.user_id THEN m.score_b ELSE m.score_a END)
                    FROM matches AS m
                    WHERE m.status = 'completed'
                      AND (m.player_a_id = pr.user_id OR m.player_b_id = pr.user_id)
                ), 0),
                points = COALESCE((
                    SELECT SUM(
                        CASE
                            WHEN m.score_a = m.score_b THEN 1
                            WHEN (m.player_a_id = pr.user_id AND m.score_a > m.score_b)
                              OR (m.player_b_id = pr.user_id AND m.score_b > m.score_a) THEN 3
                            ELSE 0
                        END
                    )
                    FROM matches AS m
                    WHERE m.status = 'completed'
                      AND (m.player_a_id = pr.user_id OR m.player_b_id = pr.user_id)
                ), 0)
            """
        )
    )


def downgrade() -> None:
    op.drop_column("player_ratings", "points")
    op.drop_column("player_ratings", "goals_against")
    op.drop_column("player_ratings", "goals_for")
    op.drop_column("player_ratings", "draws")
