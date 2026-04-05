from app.core.exceptions import NotFoundException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.like import Like
from app.models.thread import Thread
from app.models.user import User


async def toggle_like_thread(db: AsyncSession, thread_id: int, current_user: User) -> dict:
    result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalars().first()

    if not thread:
        raise NotFoundException("Thread not found")

    result = await db.execute(
        select(Like).where(Like.user_id == current_user.id, Like.thread_id == thread_id)
    )
    existing = result.scalars().first()

    if existing:
        await db.delete(existing)
        await db.commit()
        liked = False
    else:
        like = Like(user_id=current_user.id, thread_id=thread_id)
        db.add(like)
        await db.commit()
        liked = True

    count = (
        await db.execute(select(func.count(Like.id)).where(Like.thread_id == thread_id))
    ).scalar() or 0

    return {"liked": liked, "like_count": count}
