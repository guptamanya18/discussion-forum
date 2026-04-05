import logging
from datetime import datetime
from typing import Literal, Optional
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.like import Like
from app.models.thread import Thread
from app.models.user import User
from app.schemas.like import LikeResponse, LikeUserResponse
from app.schemas.thread import ThreadCreate, ThreadList, ThreadListPaginated, ThreadResponse, ThreadUpdate
from app.core.dependencies import get_current_user, get_current_user_optional
from app.core.permissions import ensure_owner_or_staff, ensure_can_delete
from app.core.exceptions import NotFoundException, NotAuthorizedException, BadRequestException
from app.services.like_service import toggle_like_thread
from app.kafka_producer import kafka_producer

logger = logging.getLogger("thread_service.routes")

router = APIRouter(prefix="/threads", tags=["Threads"])


def _build_keyword_filter(search: str):
    """Build a filter requiring every keyword to appear in title, description, or tags."""
    keywords = search.strip().split()
    if not keywords:
        return None
    conditions = []
    for word in keywords:
        pattern = f"%{word}%"
        conditions.append(
            or_(
                Thread.title.ilike(pattern),
                Thread.description.ilike(pattern),
                Thread.tags.ilike(pattern),
            )
        )
    return and_(*conditions)

COMMUNITY_SERVICE_URL = "http://community_service:8006"
COMMENT_SERVICE_URL = "http://comment_service:8005"

@router.post("", response_model=ThreadResponse)
async def create_thread(
    thread: ThreadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if thread.community_id is not None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{COMMUNITY_SERVICE_URL}/communities/{thread.community_id}")
            if resp.status_code != 200:
                raise BadRequestException("Community not found")
            community_data = resp.json()

    db_thread = Thread(
        title=thread.title,
        description=thread.description,
        tags=",".join(thread.tags) if thread.tags else None,
        community_id=thread.community_id,
        status="open",
        created_by=current_user.id,
    )

    db.add(db_thread)
    await db.commit()

    result = await db.execute(
        select(Thread).options(selectinload(Thread.author)).where(Thread.id == db_thread.id)
    )
    created = result.scalars().first()

    # Notify community owner when a thread is posted in their community
    if thread.community_id is not None:
        community_owner_id = community_data.get("created_by")
        if community_owner_id and community_owner_id != current_user.id:
            community_name = community_data.get("name", "")
            await kafka_producer.send("thread-events", {
                "event": "thread_in_community",
                "user_id": community_owner_id,
                "type": "community_thread",
                "message": f"{current_user.username} posted '{created.title}' in your community '{community_name}'",
                "reference_id": created.id,
            })

    thread_response = {
        "id": created.id,
        "title": created.title,
        "description": created.description,
        "tags": created.tags.split(",") if created.tags else None,
        "status": created.status,
        "community_id": created.community_id,
        "author": {"id": created.author.id, "username": created.author.username, "avatar": created.author.avatar},
        "created_at": str(created.created_at),
        "updated_at": str(created.updated_at),
    }

    # Broadcast new thread to all connected clients
    await kafka_producer.send("thread-events", {
        "broadcast": True,
        "type": "new_thread",
        "thread": thread_response,
    })

    return thread_response


@router.get("", response_model=ThreadListPaginated)
async def list_threads(
    skip: int = 0,
    limit: int = 10,
    sort_by: Literal["newest", "oldest", "most_liked"] = "newest",
    search: Optional[str] = None,
    tag: Optional[str] = None,
    community_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    like_counts = (
        select(Like.thread_id.label("thread_id"), func.count(Like.id).label("like_count"))
        .where(Like.thread_id.is_not(None))
        .group_by(Like.thread_id)
        .subquery()
    )
    like_count_col = func.coalesce(like_counts.c.like_count, 0)

    base_query = (
        select(Thread)
        .where(Thread.deleted_at.is_(None))
    )

    if search:
        keyword_filter = _build_keyword_filter(search)
        if keyword_filter is not None:
            base_query = base_query.where(keyword_filter)

    if tag:
        base_query = base_query.where(Thread.tags.ilike(f"%{tag}%"))
    if community_id is not None:
        base_query = base_query.where(Thread.community_id == community_id)

    # Total count (same filters, no pagination)
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar()

    query = (
        select(Thread, like_count_col.label("like_count"))
        .options(selectinload(Thread.author))
        .outerjoin(like_counts, like_counts.c.thread_id == Thread.id)
        .where(Thread.deleted_at.is_(None))
    )

    if search:
        keyword_filter = _build_keyword_filter(search)
        if keyword_filter is not None:
            query = query.where(keyword_filter)

    if tag:
        query = query.where(Thread.tags.ilike(f"%{tag}%"))
    if community_id is not None:
        query = query.where(Thread.community_id == community_id)
    if sort_by == "oldest":
        query = query.order_by(Thread.created_at.asc())
    elif sort_by == "most_liked":
        query = query.order_by(like_count_col.desc(), Thread.created_at.desc())
    else:
        query = query.order_by(Thread.created_at.desc())

    rows = (await db.execute(query.offset(skip).limit(limit))).all()

    # Fetch comment counts from comment_service
    comment_counts = {}
    if rows:
        thread_ids = ",".join(str(t.id) for t, _ in rows)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{COMMENT_SERVICE_URL}/comments/thread-counts?thread_ids={thread_ids}")
                if resp.status_code == 200:
                    comment_counts = {int(k): v for k, v in resp.json().items()}
        except Exception:
            pass

    return {
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "tags": t.tags.split(",") if t.tags else None,
                "status": t.status,
                "community_id": t.community_id,
                "author": {"id": t.author.id, "username": t.author.username, "avatar": t.author.avatar},
                "created_at": t.created_at,
                "like_count": like_count,
                "reply_count": comment_counts.get(t.id, 0),
            }
            for t, like_count in rows
        ],
        "total": total,
    }


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    like_count_sub = (
        select(func.count(Like.id))
        .where(Like.thread_id == Thread.id)
        .correlate(Thread)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Thread, like_count_sub.label("like_count"))
        .options(selectinload(Thread.author))
        .where(Thread.id == thread_id)
        .where(Thread.deleted_at.is_(None))
    )
    row = result.first()
    if not row:
        raise NotFoundException("Thread not found")
    thread, like_count = row

    liked_by_me = False
    if current_user:
        existing = (
            await db.execute(
                select(Like.id).where(Like.user_id == current_user.id, Like.thread_id == thread_id)
            )
        ).scalars().first()
        liked_by_me = existing is not None

    # Fetch comment count from comment_service
    reply_count = 0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{COMMENT_SERVICE_URL}/comments/thread-counts?thread_ids={thread_id}")
            if resp.status_code == 200:
                reply_count = resp.json().get(str(thread_id), 0)
    except Exception:
        pass

    return {
        "id": thread.id,
        "title": thread.title,
        "description": thread.description,
        "tags": thread.tags.split(",") if thread.tags else None,
        "status": thread.status,
        "community_id": thread.community_id,
        "author": {"id": thread.author.id, "username": thread.author.username, "avatar": thread.author.avatar},
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
        "like_count": like_count,
        "liked_by_me": liked_by_me,
        "reply_count": reply_count,
    }


@router.put("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: int,
    update: ThreadUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Thread)
        .options(selectinload(Thread.author))
        .where(Thread.id == thread_id)
        .where(Thread.deleted_at.is_(None))
    )
    thread = result.scalars().first()
    if not thread:
        raise NotFoundException("Thread not found")
    if current_user.id != thread.created_by:
        raise NotAuthorizedException("You can only edit your own threads")

    if update.title is not None:
        thread.title = update.title
    if update.description is not None:
        thread.description = update.description
    if update.status is not None:
        thread.status = update.status
    if update.tags is not None:
        thread.tags = ",".join(update.tags)

    await db.commit()

    result = await db.execute(
        select(Thread).options(selectinload(Thread.author)).where(Thread.id == thread_id)
    )
    updated = result.scalars().first()

    # Broadcast thread edit to all connected clients
    await kafka_producer.send("thread-events", {
        "broadcast": True,
        "type": "thread_edited",
        "thread_id": updated.id,
        "title": updated.title,
        "description": updated.description,
        "tags": updated.tags.split(",") if updated.tags else None,
    })

    return {
        "id": updated.id,
        "title": updated.title,
        "description": updated.description,
        "tags": updated.tags.split(",") if updated.tags else None,
        "status": updated.status,
        "community_id": updated.community_id,
        "author": {"id": updated.author.id, "username": updated.author.username, "avatar": updated.author.avatar},
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
    }


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Thread).options(selectinload(Thread.author)).where(Thread.id == thread_id).where(Thread.deleted_at.is_(None))
    )
    thread = result.scalars().first()
    if not thread:
        raise NotFoundException("Thread not found")

    ensure_can_delete(current_user, thread.created_by, thread.author.role if thread.author else "member")
    thread.deleted_at = datetime.utcnow()
    await db.commit()

    if thread.created_by != current_user.id:
        await kafka_producer.send("thread-events", {
            "event": "thread_deleted",
            "user_id": thread.created_by,
            "type": "thread_deleted",
            "message": f"Your thread '{thread.title}' was removed by a moderator",
            "reference_id": thread_id,
        })

    # Broadcast deletion to all connected clients
    await kafka_producer.send("thread-events", {
        "event": "thread_deleted_broadcast",
        "broadcast": True,
        "type": "thread_deleted",
        "thread_id": thread_id,
    })
    return {"message": "Thread deleted successfully"}


@router.post("/{thread_id}/like")
async def like_thread_endpoint(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await toggle_like_thread(db, thread_id, current_user)

    # Broadcast like count update to all connected clients
    await kafka_producer.send("thread-events", {
        "broadcast": True,
        "type": "thread_like_update",
        "thread_id": thread_id,
        "like_count": result["like_count"],
    })

    if result["liked"]:
        thread = (await db.execute(select(Thread).where(Thread.id == thread_id))).scalars().first()
        if thread and thread.created_by != current_user.id:
            await kafka_producer.send("thread-events", {
                "event": "thread_liked",
                "user_id": thread.created_by,
                "actor_id": current_user.id,
                "type": "thread_like",
                "message": f"{current_user.username} liked your thread",
                "reference_id": thread_id,
            })
    return result

    
@router.get("/{thread_id}/likes", response_model=list[LikeUserResponse])
async def get_thread_likes(thread_id: int, db: AsyncSession = Depends(get_db)):
    thread = (
        await db.execute(
            select(Thread).where(Thread.id == thread_id).where(Thread.deleted_at.is_(None))
        )
    ).scalars().first()
    if not thread:
        raise NotFoundException("Thread not found")

    result = await db.execute(
        select(User).join(Like, Like.user_id == User.id).where(Like.thread_id == thread_id)
    )
    return result.scalars().all()