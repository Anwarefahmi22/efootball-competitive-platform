from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RoomRead(BaseModel):
    exists: bool
    room_id: UUID | None = None
    tournament_id: UUID
    is_member: bool
    is_organizer: bool
    member_count: int
    created_at: datetime | None = None


class RoomMessageRead(BaseModel):
    id: UUID
    author_id: UUID
    author_name: str
    author_avatar_url: str | None = None
    body: str | None = None
    has_image: bool = False
    can_delete: bool = False
    created_at: datetime
