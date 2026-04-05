import httpx
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.exceptions import NotAuthorizedException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM

security = HTTPBearer()

USER_SERVICE_URL = "http://user_service:8002"


async def _sync_user_from_user_service(user_id: int, token: str, db: AsyncSession) -> User | None:
    """Fetch user from user_service, create or update the local copy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{USER_SERVICE_URL}/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()

            result = await db.execute(select(User).where(User.id == data["id"]))
            user = result.scalars().first()
            if user:
                user.username = data["username"]
                user.email = data["email"]
                user.role = data.get("role", "member")
                user.is_active = 1 if data.get("is_active", True) else 0
            else:
                user = User(
                    id=data["id"],
                    username=data["username"],
                    email=data["email"],
                    role=data.get("role", "member"),
                    is_active=1 if data.get("is_active", True) else 0,
                    hashed_password="synced",
                )
                db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise NotAuthorizedException("Invalid token")
    except JWTError:
        raise NotAuthorizedException("Invalid token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()

    if user is None:
        user = await _sync_user_from_user_service(int(user_id), token, db)
    # Local copy is kept fresh by Kafka consumer — no need to HTTP-sync every request

    if user is None:
        raise NotAuthorizedException("User not found")

    return user
