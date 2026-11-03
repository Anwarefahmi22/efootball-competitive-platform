"""Tournament rooms («مجموعة البطولة»): members-only discussion per tournament.

Revision ID: 022_tournament_rooms
Revises: 021_refresh_sessions
Create Date: 2026-11-03

Creates tournament_rooms + room_messages (see app.models.room). The
room is created with its tournament when the creator leaves the
create_room option on; it is removed with all its messages when the
tournament is deleted (FK CASCADE) and by the daily maintenance purge
after 7 days without tournament or room activity. Message photos ride
the existing media pipeline (media_files rows when MEDIA_BACKEND=db),
exactly like post images.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "022_tournament_rooms"
down_revision = "021_refresh_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tournament_rooms",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tournament_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tournaments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tournament_id", name="uq_tournament_rooms_tournament"),
    )
    op.create_table(
        "room_messages",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "room_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tournament_rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("image_path", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_room_messages_room_id", "room_messages", ["room_id"])
    op.create_index(
        "ix_room_messages_room_created", "room_messages", ["room_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_room_messages_room_created", table_name="room_messages")
    op.drop_index("ix_room_messages_room_id", table_name="room_messages")
    op.drop_table("room_messages")
    op.drop_table("tournament_rooms")
