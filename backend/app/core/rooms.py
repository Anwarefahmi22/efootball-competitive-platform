import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media import delete_media_db, is_media_ref, parse_media_ref
from app.db.session import AsyncSessionLocal
from app.models.match import Match
from app.models.room import RoomMessage, TournamentRoom
from app.models.tournament import Tournament

logger = logging.getLogger(__name__)

ROOM_INACTIVITY_LIMIT = timedelta(days=7)


async def delete_room_and_media(db: AsyncSession, room: TournamentRoom) -> None:
    """Delete a room, its messages, and any DB-stored message photos.

    Mirrors post deletion (AUD-08): media_files rows are removed
    explicitly; filesystem-track files follow the existing convention
    and are left to the storage lifecycle. The caller commits.
    """
    result = await db.execute(
        select(RoomMessage.image_path).where(
            RoomMessage.room_id == room.id, RoomMessage.image_path.is_not(None)
        )
    )
    for (image_path,) in result.all():
        if image_path and is_media_ref(image_path):
            await delete_media_db(db, parse_media_ref(image_path))
    await db.delete(room)
    await db.flush()


async def purge_inactive_rooms() -> int:
    """Delete rooms whose tournament AND room have been silent for 7 days.

    Activity is the latest of: tournament.updated_at, the tournament's
    latest match update, the room's latest message, and the room's own
    creation — the same activity definition the tournament inactivity
    canceller uses, extended with room messages so a live conversation
    is never purged from under its members. Runs from the daily
    /internal/maintenance cron alongside cancel_inactive_tournaments.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - ROOM_INACTIVITY_LIMIT
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(
                    TournamentRoom,
                    Tournament.updated_at.label("tournament_activity"),
                    func.max(Match.updated_at).label("last_match_activity"),
                    func.max(RoomMessage.created_at).label("last_message_activity"),
                )
                .join(Tournament, Tournament.id == TournamentRoom.tournament_id)
                .outerjoin(Match, Match.tournament_id == Tournament.id)
                .outerjoin(RoomMessage, RoomMessage.room_id == TournamentRoom.id)
                .group_by(TournamentRoom.id, Tournament.updated_at)
            )
            expired: list[TournamentRoom] = []
            for room, tournament_activity, last_match_activity, last_message_activity in result.all():
                last_activity = max(
                    room.created_at,
                    tournament_activity,
                    last_match_activity or room.created_at,
                    last_message_activity or room.created_at,
                )
                if last_activity <= cutoff:
                    expired.append(room)
            for room in expired:
                await delete_room_and_media(db, room)
            if expired:
                await db.commit()
                logger.info("Purged %d inactive tournament rooms", len(expired))
            return len(expired)
    except SQLAlchemyError:
        logger.exception("Tournament room purge failed")
        return 0
