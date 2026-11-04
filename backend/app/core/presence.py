"""Presence: online state, last-seen and real activity time.

The client sends a lightweight heartbeat while a logged-in page is
visible. The server stamps ``last_seen_at`` and accrues *activity*
time conservatively: only the gap between two heartbeats counts, and
only when it is at most ``ACCRUE_CAP`` — a tab left open overnight
adds nothing beyond the final capped slice.

A player who turns on ``presence_hidden`` is masked everywhere:
``is_online`` reads False and ``last_seen_at`` reads None, exactly as
if they had never been seen.
"""
from datetime import datetime, timedelta, timezone

from app.models.user import User

ONLINE_WINDOW = timedelta(minutes=2)
ACCRUE_CAP = timedelta(seconds=90)


def apply_heartbeat(user: User, now: datetime | None = None) -> None:
    """Stamp ``user`` as seen now and accrue the capped gap since the
    previous heartbeat into ``active_seconds``."""
    now = now or datetime.now(timezone.utc)
    last = user.last_seen_at
    if last is not None:
        gap = now - last
        if timedelta(0) < gap <= ACCRUE_CAP:
            user.active_seconds = (user.active_seconds or 0) + int(gap.total_seconds())
    user.last_seen_at = now


def presence_view(user: User, now: datetime | None = None) -> tuple[bool, datetime | None]:
    """(is_online, last_seen_at) as other players may see them —
    fully masked when the player hides their presence."""
    if user.presence_hidden:
        return False, None
    now = now or datetime.now(timezone.utc)
    last = user.last_seen_at
    is_online = last is not None and (now - last) <= ONLINE_WINDOW
    return is_online, last
