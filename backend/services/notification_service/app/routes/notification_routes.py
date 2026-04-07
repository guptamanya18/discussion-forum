"""This file handles requests to see or clear notifications."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationEmit, NotificationResponse, NotificationListPaginated, UnreadCount
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException
from app.ws_manager import manager

logger = logging.getLogger("notification_service.routes")

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/emit")
async def emit_notification(body: NotificationEmit, db: AsyncSession = Depends(get_db)):
    """Internal endpoint — other services call this to create and push a notification."""
    notif = Notification(
        user_id=body.user_id,
        type=body.type,
        message=body.message,
        reference_id=body.reference_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    await manager.send_to_user(body.user_id, {
        "id": notif.id,
        "type": notif.type,
        "message": notif.message,
        "reference_id": notif.reference_id,
        "is_read": False,
        "created_at": str(notif.created_at),
    })

    return {"id": notif.id}


@router.get("", response_model=NotificationListPaginated)
async def list_notifications(
    skip: int = 0,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Total count
    count_result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return {"items": result.scalars().all(), "total": total}


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = (
        await db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == current_user.id)
            .where(Notification.is_read == False)
        )
    ).scalar()
    return {"count": count}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user.id)
    )
    notif = result.scalars().first()
    if not notif:
        raise NotFoundException("Notification not found")
    notif.is_read = True
    await db.commit()
    return {"message": "Marked as read"}


@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}
