import logging
import os
import uuid
import shutil
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserRoleUpdate
from app.core.dependencies import get_current_user
from app.core.permissions import ensure_role, validate_role
from app.core.exceptions import NotFoundException, BadRequestException, DuplicateException
from app.services.user_service import create_user
from app.kafka_producer import kafka_producer
import httpx

UPLOAD_DIR = "/app/uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

logger = logging.getLogger("user_service.users")

NOTIFICATION_SERVICE_URL = "http://notification_service:8007"

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user)


@router.post("/init-admin")
async def init_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote the caller to admin. Only works when no admin exists yet."""
    existing_admin = await db.execute(
        select(User).where(User.role == "admin").limit(1)
    )
    if existing_admin.scalars().first():
        raise BadRequestException("Admin already exists")

    current_user.role = "admin"
    await db.commit()
    await db.refresh(current_user)
    return {"message": f"User '{current_user.username}' is now admin"}


@router.put("/profile")
async def update_profile(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if update.name is not None:
        current_user.name = update.name
    if update.bio is not None:
        current_user.bio = update.bio
    if update.avatar is not None:
        current_user.avatar = update.avatar

    await db.commit()
    await db.refresh(current_user)

    # Notify other services about user data change
    await kafka_producer.send("user-events", {
        "type": "user_updated",
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active != 0,
    })

    return {"message": "Profile updated"}


@router.post("/avatar/upload")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestException(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise BadRequestException("File too large. Max 5 MB.")

    filename = f"{current_user.id}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    # Delete old avatar file if it exists
    if current_user.avatar and current_user.avatar.startswith("/uploads/avatars/"):
        old_path = "/app" + current_user.avatar
        if os.path.exists(old_path):
            os.remove(old_path)

    current_user.avatar = f"/uploads/avatars/{filename}"
    await db.commit()
    await db.refresh(current_user)

    # Broadcast avatar update to frontend clients
    await kafka_producer.send("user-events", {
        "type": "avatar_update",
        "user_id": current_user.id,
        "avatar": current_user.avatar,
        "broadcast": True,
    })

    # Notify other services about user data change
    await kafka_producer.send("user-events", {
        "type": "user_updated",
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active != 0,
    })

    return {"avatar": current_user.avatar}


# shows total users and count of each role
@router.get("/admin/stats")
async def admin_stats(
    current_user: User=Depends(get_current_user),
    db: AsyncSession=Depends(get_db),
):
    ensure_role(current_user, "admin")

    total_users=(await db.execute(select(func.count(User.id)))).scalar()
    role_counts = (await db.execute(
        select(User.role,func.count(User.id)).group_by(User.role)
    )).all()

    return {
        "total_users": total_users,
        "roles": {role: count for role, count in role_counts},
    }


@router.get("/admin/users")
async def admin_list_users(
    skip: int=0,
    limit: int=20,
    role: str | None=None,
    search: str | None=None,
    current_user:User=Depends(get_current_user),
    db:AsyncSession=Depends(get_db),
):
    
    ensure_role(current_user, "admin")

    query=select(User)

    if role:
        query=query.where(User.role==role)
    if search:
        query=query.where(User.username.ilike(f"%{search}%"))

    query=query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result=await db.execute(query)
    users=result.scalars().all()

    return [
        {"id": u.id,
         "username": u.username,
         "email": u.email,
         "role":u.role,
         "avatar": u.avatar,
         "is_active": u.is_active != 0,
         "created_at":u.created_at,
        }
        for u in users
    ]


@router.post("/admin/users/{user_id}/status")
async def admin_set_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ensure_role(current_user, "admin")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise NotFoundException("User not found")

    if user.id == current_user.id:
        raise BadRequestException("Cannot change your own status")

    user.is_active = 1 if is_active else 0
    await db.commit()

    # Notify other services about user data change
    await kafka_producer.send("user-events", {
        "type": "user_updated",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar,
        "is_active": user.is_active != 0,
    })

    # Notify user of status change
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{NOTIFICATION_SERVICE_URL}/notifications/emit", json={
                "user_id": user_id,
                "type": "account_deactivated" if not is_active else "account_activated",
                "message": f"Your account has been {'deactivated' if not is_active else 'activated'} by an admin",
                "reference_id": user_id,
            })
    except Exception:
        pass

    return {"message": f"User {'activated' if is_active else 'deactivated'}"}


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id:int,
    current_user:User=Depends(get_current_user),
    db:AsyncSession=Depends(get_db),
):
    
    ensure_role(current_user,"admin")

    result=await db.execute(select(User).where(User.id==user_id))
    user=result.scalars().first()

    if not user:
        raise NotFoundException("User not found")
    
    if user.id==current_user.id:
        raise BadRequestException("Cannot delete yourself")

    old_username = user.username

    # Notify the user before deleting (so we can still reference their id)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{NOTIFICATION_SERVICE_URL}/notifications/emit", json={
                "user_id": user_id,
                "type": "account_deleted",
                "message": f"Your account '{old_username}' has been deleted by an admin",
                "reference_id": user_id,
            })
    except Exception:
        pass

    # Hard delete — permanently remove the user from the database
    await db.delete(user)
    await db.commit()
    logger.info("Admin '%s' permanently deleted user '%s' (id=%d)", current_user.username, old_username, user_id)

    return {"message": "User deleted"}


@router.get("/mod/users")
async def mod_list_users(
    skip: int=0,
    limit: int=20,
    search: str | None=None,
    role: str | None=None,
    current_user:User=Depends(get_current_user),
    db:AsyncSession=Depends(get_db),
):
    ensure_role(current_user,"admin","moderator")

    query=select(User)
    if search:
        query=query.where(User.username.ilike(f"%{search}%"))
    if role:
        query=query.where(User.role==role)

    total=(await db.execute(select(func.count(User.id)).select_from(query.subquery()))).scalar()

    query=query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result=await db.execute(query)
    users=result.scalars().all()

    return{
        "total": total,
        "skip": skip,
        "limit": limit,
        "users":[
            {
                "id":u.id,
                "username": u.username,
                "email": u.email,
                "role":u.role,
                "avatar": u.avatar,
                "created_at":u.created_at,
            }
            for u in users
        ],
    }


@router.get("/mod/stats")
async def mod_stats(
    current_user:User=Depends(get_current_user),
    db:AsyncSession=Depends(get_db),
):
    ensure_role(current_user,"admin","moderator")

    total_users=(await db.execute(select(func.count(User.id)))).scalar()
    role_counts=(await db.execute(
        select(User.role,func.count(User.id)).group_by(User.role)
    )).all()

    recent_users=(await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .limit(5)
    )).scalars().all()

    return{
        "total_users": total_users,
        "roles": {role: count for role,count in role_counts},
        "recent_users":[
            {
                "id": u.id,
                "username": u.username,
                "avatar": u.avatar,
                "role": u.role,
                "created_at": u.created_at,
            }
            for u in recent_users
        ],
    }


@router.get("/me/dashboard")
async def member_dashboard(
    current_user:User=Depends(get_current_user),
    db:AsyncSession=Depends(get_db),
):
    return{
        "user":{
            "id":current_user.id,
            "username":current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "name": current_user.name,
            "bio": current_user.bio,
            "avatar": current_user.avatar,
            "created_at": current_user.created_at,
        },
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(user_id: int, db: AsyncSession=Depends(get_db)):
    result=await db.execute(select(User).where(User.id==user_id))
    user=result.scalars().first()

    if not user:
        raise NotFoundException("User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ensure_role(current_user, "admin")

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalars().first()

    if not target_user:
        raise NotFoundException("User not found")

    old_role = target_user.role
    target_user.role = validate_role(payload.role)

    await db.commit()
    await db.refresh(target_user)

    # Notify other services about user data change
    await kafka_producer.send("user-events", {
        "type": "user_updated",
        "user_id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "role": target_user.role,
        "avatar": target_user.avatar,
        "is_active": target_user.is_active != 0,
    })

    # Notify user about role change
    if old_role != target_user.role and target_user.id != current_user.id:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{NOTIFICATION_SERVICE_URL}/notifications/emit", json={
                    "user_id": target_user.id,
                    "type": "role_change",
                    "message": f"Your role has been changed from '{old_role}' to '{target_user.role}' by an admin",
                    "reference_id": target_user.id,
                })
        except Exception:
            pass

    return target_user
