"""media files stored in the database (Vercel track)

Revision ID: 015_media_files
Revises: 014_trust_events
Create Date: 2026-10-30

Why this migration exists
-------------------------
Post images and avatars are written to the local filesystem
(backend/storage/) and served from disk. That works on a long-running
server (Botkeep/Render) but not on Vercel: serverless filesystems are
ephemeral, so uploads would vanish between invocations.

Match evidence already solved this exact problem in migration 012 by
keeping image bytes in Postgres. This revision adds the equivalent table
for post/avatar media: ``media_files`` (id, content_type, data,
created_at). The application only reads/writes it when the environment
flag MEDIA_BACKEND=db; on the default MEDIA_BACKEND=fs track behaviour is
completely unchanged and the table stays empty, so this migration is safe
to apply on both tracks.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_media_files"
down_revision: Union[str, None] = "014_trust_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("media_files")
