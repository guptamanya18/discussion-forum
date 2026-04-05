import logging
from datetime import datetime
from typing import Literal, Optional
import re
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.permissions import ensure_owner_or_staff, ensure_can_delete
from app.core.exceptions import NotFoundException, NotAuthorizedException, BadRequestException, ForbiddenException
from app.database import get_db
from app.models.comment import Comment
from app.models.like import Like
from app.models.user import User
from app.schemas.comment import (
    CommentCreate,
    CommentList,
    CommentResponse,
    CommentTree,
    CommentUpdate,
)
from app.schemas.like import LikeResponse, LikeUserResponse
from app.services.like_service import toggle_like_comment
from app.kafka_producer import kafka_producer
import httpx

THREAD_SERVICE_URL = "http://thread_service:8003"

logger = logging.getLogger("comment_service.routes")

router = APIRouter(tags=["Comments"])


@router.post("/comments", response_model=CommentResponse)
async def create_comment(
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if comment.parent_comment_id is not None:
        result = await db.execute(
            select(Comment)
            .where(Comment.id == comment.parent_comment_id)
            .where(Comment.deleted_at.is_(None))
        )
        parent = result.scalars().first()
        if not parent:
            raise NotFoundException("Parent comment not found")
        if parent.thread_id != comment.thread_id:
            raise BadRequestException(
                "Parent comment must belong to the same thread"
            )

    db_comment = Comment(
        content=comment.content,
        thread_id=comment.thread_id,
        author_id=current_user.id,
        parent_comment_id=comment.parent_comment_id,
    )
    db.add(db_comment)
    await db.commit()

    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == db_comment.id)
    )
    created = result.scalars().first()

    if comment.parent_comment_id:
        parent_result = await db.execute(
            select(Comment).where(Comment.id == comment.parent_comment_id)
        )
        parent = parent_result.scalars().first()
        if parent and parent.author_id != current_user.id:
            await kafka_producer.send("comment-events", {
                "event": "comment_reply",
                "user_id": parent.author_id,
                "type": "comment_reply",
                "message": f"{current_user.username} replied to your comment",
                "reference_id": created.id,
            })

    # Notify thread author for ANY comment/reply on their thread
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{THREAD_SERVICE_URL}/threads/{comment.thread_id}")
            if resp.status_code == 200:
                thread_data = resp.json()
                thread_author_id = thread_data.get("author", {}).get("id")
                # Don't notify if: thread author is the commenter,
                # or thread author is already notified as parent comment author
                already_notified = (
                    comment.parent_comment_id
                    and parent
                    and parent.author_id == thread_author_id
                )
                if thread_author_id and thread_author_id != current_user.id and not already_notified:
                    await kafka_producer.send("comment-events", {
                        "event": "new_comment",
                        "user_id": thread_author_id,
                        "type": "new_comment",
                        "message": f"{current_user.username} commented on your thread",
                        "reference_id": created.id,
                    })
    except Exception:
        pass

    # Broadcast new comment to all clients viewing this thread
    await kafka_producer.send("comment-events", {
        "broadcast": True,
        "type": "new_comment_broadcast",
        "comment": {
            "id": created.id,
            "content": created.content,
            "thread_id": created.thread_id,
            "author": {"id": created.author.id, "username": created.author.username, "avatar": created.author.avatar},
            "parent_comment_id": created.parent_comment_id,
            "created_at": str(created.created_at),
            "updated_at": str(created.updated_at),
            "like_count": 0,
            "liked_by_me": False,
            "reply_count": 0,
            "replies": [],
        },
    })

    # Detect @mentions and notify mentioned users
    mentions = set(re.findall(r"@(\w+)", comment.content))
    if mentions:
        mentioned_users = (
            await db.execute(select(User).where(User.username.in_(mentions)))
        ).scalars().all()
        for mentioned in mentioned_users:
            if mentioned.id != current_user.id:
                await kafka_producer.send("comment-events", {
                    "event": "mention",
                    "user_id": mentioned.id,
                    "type": "mention",
                    "message": f"{current_user.username} mentioned you in a comment",
                    "reference_id": created.id,
                })

    return created


@router.get("/comments/thread-counts")
async def get_thread_comment_counts(
    thread_ids: str,
    db: AsyncSession = Depends(get_db),
):
    ids = [int(x) for x in thread_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(Comment.thread_id, func.count(Comment.id))
            .where(Comment.thread_id.in_(ids))
            .where(Comment.deleted_at.is_(None))
            .group_by(Comment.thread_id)
        )
    ).all()
    return {str(tid): cnt for tid, cnt in rows}


@router.get("/comments/{comment_id}", response_model=CommentResponse)
async def get_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id)
        .where(Comment.deleted_at.is_(None))
    )
    comment = result.scalars().first()
    if not comment:
        raise NotFoundException("Comment not found")
    return comment


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    update: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id)
        .where(Comment.deleted_at.is_(None))
    )
    comment = result.scalars().first()
    if not comment:
        raise NotFoundException("Comment not found")
    if current_user.id != comment.author_id:
        raise NotAuthorizedException("You can only edit your own comments")

    if update.content is not None:
        comment.content = update.content

    await db.commit()

    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id)
    )
    updated = result.scalars().first()

    # Broadcast comment edit to all connected clients
    await kafka_producer.send("comment-events", {
        "broadcast": True,
        "type": "comment_edited",
        "comment_id": updated.id,
        "thread_id": updated.thread_id,
        "content": updated.content,
    })

    return updated


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id)
        .where(Comment.deleted_at.is_(None))
    )
    comment = result.scalars().first()
    if not comment:
        raise NotFoundException("Comment not found")

    ensure_can_delete(current_user, comment.author_id, comment.author.role if comment.author else "member")

    # Recursively find all descendant comment IDs
    all_ids = [comment_id]
    to_check = [comment_id]
    while to_check:
        children = (
            await db.execute(
                select(Comment.id)
                .where(Comment.parent_comment_id.in_(to_check))
                .where(Comment.deleted_at.is_(None))
            )
        ).scalars().all()
        all_ids.extend(children)
        to_check = list(children)

    # Soft-delete all (parent + descendants)
    now = datetime.utcnow()
    for cid in all_ids:
        c = (await db.execute(select(Comment).where(Comment.id == cid))).scalars().first()
        if c and c.deleted_at is None:
            c.deleted_at = now
    await db.commit()

    deleted_count = len(all_ids)

    if comment.author_id != current_user.id:
        await kafka_producer.send("comment-events", {
            "event": "comment_deleted",
            "user_id": comment.author_id,
            "type": "comment_deleted",
            "message": f"Your comment was removed by a moderator",
            "reference_id": comment_id,
        })

    # Broadcast deletion to all connected clients
    await kafka_producer.send("comment-events", {
        "event": "comment_deleted_broadcast",
        "broadcast": True,
        "type": "comment_deleted",
        "comment_id": comment_id,
        "thread_id": comment.thread_id,
        "deleted_count": deleted_count,
    })
    return {"message": f"Comment and {deleted_count - 1} replies deleted successfully"}


@router.get("/comments", response_model=list[CommentList])
async def list_comments(
    skip: int = 0,
    limit: int = 20,
    thread_id: Optional[int] = None,
    author_id: Optional[int] = None,
    sort_by: Literal["newest", "oldest", "most_liked"] = "newest",
    search:Optional[str]=None,
    db: AsyncSession = Depends(get_db),
):
    like_counts = (
        select(Like.comment_id.label("comment_id"), func.count(Like.id).label("like_count"))
        .where(Like.comment_id.is_not(None))
        .group_by(Like.comment_id)
        .subquery()
    )
    like_count_col = func.coalesce(like_counts.c.like_count, 0)

    query = (
        select(Comment, like_count_col.label("like_count"))
        .options(selectinload(Comment.author))
        .outerjoin(like_counts, like_counts.c.comment_id == Comment.id)
        .where(Comment.deleted_at.is_(None))
    )

    if thread_id is not None:
        query = query.where(Comment.thread_id == thread_id)
    if author_id is not None:
        query = query.where(Comment.author_id == author_id)

    if search:
        query=query.where(Comment.content.ilike(f"%{search}%"))

    if sort_by == "oldest":
        query = query.order_by(Comment.created_at.asc())
    elif sort_by == "most_liked":
        query = query.order_by(like_count_col.desc(), Comment.created_at.desc())
    else:
        query = query.order_by(Comment.created_at.desc())

    rows = (await db.execute(query.offset(skip).limit(limit))).all()
    return [
        {
            "id": c.id,
            "content": c.content,
            "thread_id": c.thread_id,
            "author": {"id": c.author.id, "username": c.author.username, "avatar": c.author.avatar},
            "parent_comment_id": c.parent_comment_id,
            "created_at": c.created_at,
            "like_count": like_count,
        }
        for c, like_count in rows
    ]


def _build_comment_tree(all_rows: list, liked_ids: set | None = None):
    if liked_ids is None:
        liked_ids = set()
    by_id = {
        c.id: {
            "id": c.id,
            "content": c.content,
            "thread_id": c.thread_id,
            "author": {"id": c.author.id, "username": c.author.username, "avatar": c.author.avatar},
            "parent_comment_id": c.parent_comment_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "like_count": lc,
            "liked_by_me": c.id in liked_ids,
            "reply_count": 0,
            "replies": [],
        }
        for c, lc in all_rows
    }
    roots = []
    for c, lc in all_rows:
        node = by_id[c.id]
        if c.parent_comment_id is not None and c.parent_comment_id in by_id:
            by_id[c.parent_comment_id]["replies"].append(node)
            by_id[c.parent_comment_id]["reply_count"] += 1
        else:
            roots.append(node)
    return roots


@router.get("/threads/{thread_id}/comments", response_model=list[CommentTree])
async def get_thread_comments(
    thread_id: int,
    skip: int = 0,
    limit: int = 50,
    sort_by: Literal["newest", "oldest"] = "oldest",
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    roots_query = (
        select(Comment)
        .where(Comment.thread_id == thread_id)
        .where(Comment.parent_comment_id.is_(None))
        .where(Comment.deleted_at.is_(None))
    )
    roots_query = roots_query.order_by(
        Comment.created_at.desc() if sort_by == "newest" else Comment.created_at.asc()
    )

    root_comments = (await db.execute(roots_query.offset(skip).limit(limit))).scalars().all()
    if not root_comments:
        return []

    root_ids = {c.id for c in root_comments}

    like_counts = (
        select(
            Like.comment_id,
            func.count(Like.id).label("like_count"),
        )
        .where(Like.comment_id.is_not(None))
        .group_by(Like.comment_id)
        .subquery()
    )

    all_rows = (
        await db.execute(
            select(Comment, func.coalesce(like_counts.c.like_count, 0).label("like_count"))
            .options(selectinload(Comment.author))
            .outerjoin(like_counts, like_counts.c.comment_id == Comment.id)
            .where(Comment.thread_id == thread_id)
            .where(Comment.deleted_at.is_(None))
            .order_by(Comment.created_at.asc())
        )
    ).all()

    liked_ids = set()
    if current_user:
        comment_ids = [c.id for c, _ in all_rows]
        if comment_ids:
            liked_rows = (
                await db.execute(
                    select(Like.comment_id).where(
                        Like.user_id == current_user.id,
                        Like.comment_id.in_(comment_ids),
                    )
                )
            ).scalars().all()
            liked_ids = set(liked_rows)

    full_tree = _build_comment_tree(all_rows, liked_ids)
    return [node for node in full_tree if node["id"] in root_ids]


@router.post("/comments/{comment_id}/like")
async def like_comment_endpoint(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await toggle_like_comment(db, comment_id, current_user)

    # Broadcast like count update to all connected clients
    comment = (await db.execute(select(Comment).where(Comment.id == comment_id))).scalars().first()
    await kafka_producer.send("comment-events", {
        "broadcast": True,
        "type": "comment_like_update",
        "comment_id": comment_id,
        "thread_id": comment.thread_id if comment else None,
        "like_count": result["like_count"],
    })

    if result["liked"] and comment and comment.author_id != current_user.id:
        await kafka_producer.send("comment-events", {
            "event": "comment_liked",
            "user_id": comment.author_id,
            "actor_id": current_user.id,
            "type": "comment_like",
            "message": f"{current_user.username} liked your comment",
            "reference_id": comment_id,
        })

    # Notify thread author when a comment on their thread is liked
    if result["liked"] and comment:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{THREAD_SERVICE_URL}/threads/{comment.thread_id}")
                if resp.status_code == 200:
                    thread_data = resp.json()
                    thread_author_id = thread_data.get("author", {}).get("id")
                    if (thread_author_id
                            and thread_author_id != current_user.id
                            and thread_author_id != comment.author_id):
                        await kafka_producer.send("comment-events", {
                            "event": "comment_liked_on_thread",
                            "user_id": thread_author_id,
                            "type": "comment_like",
                            "message": f"{current_user.username} liked a comment on your thread",
                            "reference_id": comment_id,
                        })
        except Exception:
            pass

    return result


@router.get("/comments/{comment_id}/likes", response_model=list[LikeUserResponse])
async def get_comment_likes(comment_id: int, db: AsyncSession = Depends(get_db)):
    comment = (
        await db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
            .where(Comment.deleted_at.is_(None))
        )
    ).scalars().first()
    if not comment:
        raise NotFoundException("Comment not found")

    result = await db.execute(
        select(User).join(Like, Like.user_id == User.id).where(Like.comment_id == comment_id)
    )
    return result.scalars().all()
