from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.social import PostType


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    author_name: str = ""
    post_type: PostType
    content: str | None
    has_image: bool = False
    match_id: UUID | None
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    author_id: UUID
    author_name: str = ""
    content: str
    created_at: datetime


class FollowStats(BaseModel):
    user_id: UUID
    followers_count: int
    following_count: int
    is_following: bool = False
