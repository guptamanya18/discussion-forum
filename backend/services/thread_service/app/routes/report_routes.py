"""This file handles requests for reporting inappropriate threads."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.report import Report
from app.models.thread import Thread
from app.models.user import User
from app.schemas.report import ReportCreate, ReportResponse, ReportListPaginated
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    DuplicateException,
)
from app.kafka_producer import kafka_producer

logger = logging.getLogger("thread_service.report_routes")

router = APIRouter(tags=["Reports"])


@router.post("/threads/{thread_id}/report", response_model=ReportResponse)
async def report_thread(
    thread_id: int,
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check thread exists
    thread = (
        await db.execute(
            select(Thread).where(Thread.id == thread_id, Thread.deleted_at.is_(None))
        )
    ).scalars().first()
    if not thread:
        raise NotFoundException("Thread not found")

    # Cannot report own thread
    if thread.created_by == current_user.id:
        raise BadRequestException("You cannot report your own thread")

    # Check for duplicate pending report by same user
    existing = (
        await db.execute(
            select(Report).where(
                Report.thread_id == thread_id,
                Report.reported_by == current_user.id,
                Report.status == "pending",
            )
        )
    ).scalars().first()
    if existing:
        raise DuplicateException("You have already reported this thread")

    report = Report(
        thread_id=thread_id,
        reported_by=current_user.id,
        reason=body.reason,
        details=body.details,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Notify all admins via Kafka
    admin_rows = (
        await db.execute(select(User).where(User.role == "admin"))
    ).scalars().all()

    for admin in admin_rows:
        await kafka_producer.send("thread-events", {
            "event": "thread_reported",
            "user_id": admin.id,
            "type": "thread_report",
            "message": f"{current_user.username} reported thread \"{thread.title}\" — Reason: {body.reason}",
            "reference_id": thread_id,
        })

    logger.info(
        "Thread %d reported by user %d (%s). Reason: %s",
        thread_id,
        current_user.id,
        current_user.username,
        body.reason,
    )

    return {
        "id": report.id,
        "thread_id": report.thread_id,
        "reported_by": report.reported_by,
        "reporter": {
            "id": current_user.id,
            "username": current_user.username,
            "avatar": current_user.avatar,
        },
        "reason": report.reason,
        "details": report.details,
        "status": report.status,
        "created_at": report.created_at,
        "thread_title": thread.title,
    }


@router.get("/reports", response_model=ReportListPaginated)
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise ForbiddenException("Only admin can view reports")

    query = (
        select(Report)
        .options(selectinload(Report.thread), selectinload(Report.reporter))
        .order_by(Report.created_at.desc())
    )
    count_query = select(func.count(Report.id))

    if status:
        query = query.where(Report.status == status)
        count_query = count_query.where(Report.status == status)

    total = (await db.execute(count_query)).scalar()
    rows = (await db.execute(query.offset(skip).limit(limit))).scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "thread_id": r.thread_id,
                "reported_by": r.reported_by,
                "reporter": {
                    "id": r.reporter.id,
                    "username": r.reporter.username,
                    "avatar": r.reporter.avatar,
                } if r.reporter else None,
                "reason": r.reason,
                "details": r.details,
                "status": r.status,
                "created_at": r.created_at,
                "thread_title": r.thread.title if r.thread else None,
            }
            for r in rows
        ],
        "total": total,
    }


@router.put("/reports/{report_id}/status")
async def update_report_status(
    report_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise ForbiddenException("Only admin can update reports")

    if status not in ("reviewed", "dismissed"):
        raise BadRequestException("Status must be 'reviewed' or 'dismissed'")

    report = (
        await db.execute(select(Report).where(Report.id == report_id))
    ).scalars().first()
    if not report:
        raise NotFoundException("Report not found")

    report.status = status
    await db.commit()

    return {"message": f"Report {report_id} marked as {status}"}
