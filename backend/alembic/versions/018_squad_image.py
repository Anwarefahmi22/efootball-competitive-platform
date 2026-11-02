"""Squad screenshot on profiles (Arena Star card image).

Revision ID: 018_squad_image
Revises: 017_arena_star
Create Date: 2026-11-02

Adds profiles.squad_image_url: the player's uploaded eFootball squad
screenshot (re-encoded to WebP server-side), shown on the Arena Star
card in place of the drawn formation pitch. On the Vercel track this
DDL is applied through the Neon console before the code deploy, the
same way 017 was.
"""
from alembic import op
import sqlalchemy as sa

revision = "018_squad_image"
down_revision = "017_arena_star"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("squad_image_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "squad_image_url")
