from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.user import User
from app.core.security import verify_password

async def authenticate_user(username: str, password: str, db: AsyncSession):
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalars().first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
