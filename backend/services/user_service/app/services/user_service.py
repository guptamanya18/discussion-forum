import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.exceptions import DuplicateException

logger = logging.getLogger("user_service.users")


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    result = await db.execute(
        select(User).where(
            (User.email == user.email) | (User.username == user.username)
        )
    )
    existing = result.scalars().first()
    if existing:
        raise DuplicateException("Username or email already registered")

    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info("New user registered: %s", user.username)
    return db_user
