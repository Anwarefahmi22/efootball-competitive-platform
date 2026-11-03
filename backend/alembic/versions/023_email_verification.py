"""Email verification (migration 023).

Adds ``users.email_verified`` — the email-ownership flag from the
verification-code flow, distinct from ``users.is_verified`` (the
admin-granted identity badge) — plus the ``email_verification_codes``
table holding HMAC-hashed, single-use, expiring codes.

Accounts created before this feature are grandfathered
(``email_verified = true``): they registered under the old rules and
locking them out would strand every real player. Only registrations
after the feature is enabled start unverified.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023_email_verification"
down_revision: Union[str, Sequence[str], None] = "022_tournament_rooms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    # Grandfather every pre-existing account.
    op.execute("UPDATE users SET email_verified = true")
    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verification_codes_user_id",
        "email_verification_codes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_codes_user_id",
        table_name="email_verification_codes",
    )
    op.drop_table("email_verification_codes")
    op.drop_column("users", "email_verified")
