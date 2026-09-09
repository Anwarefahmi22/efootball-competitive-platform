import mimetypes
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.auth import get_current_user
from app.core.media import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, save_post_image
from app.db.session import get_db
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
    content: str | None = Form(default=None),
    category: str = Form(default="general"),
    match_id: UUID | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PostRead:
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
        content_type = image.content_type or mimetypes.guess_type(image.filename or "")[0]
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG or PNG images accepted"
            )
        file_bytes = await image.read()
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Image exceeds 8MB limit"
            )
        extension = ".png" if content_type == "image/png" else ".jpg"
        image_path = save_post_image(file_bytes, extension)
        if category == "general":
            post_type = PostType.IMAGE
    if match_id is not None:
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
    stmt = select(Post).order_by(Post.created_at.desc()).limit(limit).offset(offset)
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
async def get_post_image(post_id: UUID, db: AsyncSession = Depends(get_db)) -> FileResponse:
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if post is None or post.image_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
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
    await db.commit()


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
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at)
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
