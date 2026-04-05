from app.core.exceptions import NotFoundException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.like import Like
from app.models.user import User


async def toggle_like_comment(db: AsyncSession, comment_id: int, current_user: User) -> dict:
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    if not result.scalars().first():
        raise NotFoundException("Comment not found")

    result = await db.execute(
        select(Like).where(Like.user_id == current_user.id, Like.comment_id == comment_id)
    )
    existing = result.scalars().first()

    if existing:
        await db.delete(existing)
        await db.commit()
        liked = False
    else:
        like = Like(user_id=current_user.id, comment_id=comment_id)
        db.add(like)
        await db.commit()
        liked = True

    count = (
        await db.execute(select(func.count(Like.id)).where(Like.comment_id == comment_id))
    ).scalar() or 0

    return {"liked": liked, "like_count": count}
