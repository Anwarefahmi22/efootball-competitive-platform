from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthThrottle(Base):
    """Sliding-window counters for auth abuse throttling.

    One row per throttle key (``login:email:<email>``, ``login:ip:<ip>``,
    ``register:ip:<ip>``). Serverless functions share no memory, so the
    counters live in Postgres next to everything else; the volume is
    trivial (one small row per distinct email/IP that ever failed).
    Logic lives in app.core.throttle.
    """

    __tablename__ = "auth_throttle"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
