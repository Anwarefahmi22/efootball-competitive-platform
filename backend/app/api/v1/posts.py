from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.core.media import (
    MAX_UPLOAD_BYTES,
    get_media_file,
    is_media_ref,
    media_backend,
    media_ref,
    normalize_image,
    parse_media_ref,
    read_upload_limited,
    save_post_image,
    save_post_image_db,
)
from app.core.throttle import enforce_quota
from app.db.session import get_db
from app.models.match import Match
from app.models.social import Comment, Post, PostLike, PostType
from app.models.user import User
from app.schemas.social import CommentCreate, CommentRead, PostRead

router = APIRouter()


async def _to_post_read(db: AsyncSession, post: Post) -> PostRead:
    author_result = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == post.author_id)
    )
    author = author_result.scalar_one_or_none()
    like_count_result = await db.execute(
        select(func.count()).select_from(PostLike).where(PostLike.post_id == post.id)
    )
    comment_count_result = await db.execute(
        select(func.count()).select_from(Comment).where(Comment.post_id == post.id)
    )
    return PostRead(
        id=post.id,
        author_id=post.author_id,
        author_name=author.display_name if author else "",
        author_avatar_url=author.profile.avatar_url if author and author.profile else None,
        author_country=author.profile.country if author and author.profile else None,
        post_type=post.post_type,
        content=post.content,
        has_image=post.image_path is not None,
        match_id=post.match_id,
        like_count=like_count_result.scalar_one(),
        comment_count=comment_count_result.scalar_one(),
        created_at=post.created_at,
    )


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str | None = Form(default=None, max_length=5000),
    category: str = Form(default="general"),
    match_id: UUID | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PostRead:
    await enforce_quota(db, f"quota:post:{current_user.id}", limit=20, window=timedelta(hours=1), lock_for=timedelta(hours=1))
    if content is not None and not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post content cannot be empty",
        )
    if not content and not image and not match_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post must have content, an image, or a linked match",
        )

    image_path = None
    category_types = {
        "achievement": PostType.ACHIEVEMENT,
        "tournament": PostType.TOURNAMENT,
        "general": PostType.GENERAL,
        "match": PostType.GENERAL,
    }
    post_type = category_types.get(category, PostType.GENERAL)
    if image is not None:
        # AUD-12/AUD-16: stream with a hard cap, then decode-verify and
        # re-encode — the declared content type is never trusted.
        raw_bytes = await read_upload_limited(image, MAX_UPLOAD_BYTES)
        try:
            file_bytes = normalize_image(raw_bytes, max_width=1600)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid image",
            )
        content_type = "image/webp"
        extension = ".webp"
        if media_backend() == "db":
            media_id = await save_post_image_db(db, file_bytes, content_type)
            image_path = media_ref(media_id)
        else:
            image_path = save_post_image(file_bytes, extension)
        if category == "general":
            post_type = PostType.IMAGE
    if match_id is not None:
        match_result = await db.execute(select(Match).where(Match.id == match_id))
        if match_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        post_type = PostType.MATCH_RESULT

    post = Post(
        author_id=current_user.id,
        post_type=post_type,
        content=content,
        image_path=image_path,
        match_id=match_id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return await _to_post_read(db, post)


@router.get("", response_model=list[PostRead])
async def list_feed(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    author_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[PostRead]:
    stmt = select(Post).order_by(Post.created_at.desc(), Post.id.desc()).limit(limit).offset(offset)
    if author_id is not None:
        stmt = stmt.where(Post.author_id == author_id)
    result = await db.execute(stmt)
    posts = result.scalars().all()
    return [await _to_post_read(db, p) for p in posts]


@router.get("/{post_id}", response_model=PostRead)
async def get_post(post_id: UUID, db: AsyncSession = Depends(get_db)) -> PostRead:
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return await _to_post_read(db, post)


@router.get("/{post_id}/image")
async def get_post_image(post_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None or post.image_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    if is_media_ref(post.image_path):
        media = await get_media_file(db, parse_media_ref(post.image_path))
        if media is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
        return Response(content=media.data, media_type=media.content_type)
    return FileResponse(post.image_path)


@router.post("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    if post_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = await db.execute(
        select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == current_user.id)
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(PostLike(post_id=post_id, user_id=current_user.id))
    try:
        await db.commit()
    except IntegrityError:
        # AUD-15: concurrent duplicate like — idempotent endpoint, the
        # desired end state already exists; resolve silently like the
        # pre-check above does.
        await db.rollback()


@router.delete("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    existing = await db.execute(
        select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == current_user.id)
    )
    like = existing.scalar_one_or_none()
    if like is not None:
        await db.delete(like)
        await db.commit()


@router.post("/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def add_comment(
    post_id: UUID,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    await enforce_quota(db, f"quota:comment:{current_user.id}", limit=60, window=timedelta(hours=1), lock_for=timedelta(hours=1))
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    if post_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    comment = Comment(post_id=post_id, author_id=current_user.id, content=payload.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentRead(
        id=comment.id,
        post_id=comment.post_id,
        author_id=comment.author_id,
        author_name=current_user.display_name,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/{post_id}/comments", response_model=list[CommentRead])
async def list_comments(post_id: UUID, db: AsyncSession = Depends(get_db)) -> list[CommentRead]:
    result = await db.execute(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at, Comment.id)
    )
    comments = result.scalars().all()
    out = []
    for c in comments:
        author_result = await db.execute(select(User).where(User.id == c.author_id))
        author = author_result.scalar_one_or_none()
        out.append(
            CommentRead(
                id=c.id,
                post_id=c.post_id,
                author_id=c.author_id,
                author_name=author.display_name if author else "",
                content=c.content,
                created_at=c.created_at,
            )
        )
    return out
