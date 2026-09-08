"""make all tournaments free and remove financial rewards"""

from alembic import op


revision = "013_free_competition"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE tournaments SET entry_fee = 0, prize_pool = 0")


def downgrade() -> None:
    pass
