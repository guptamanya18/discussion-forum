"""This defines what data is needed to create or view a report."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.schemas.user import AuthorInfo


class ReportCreate(BaseModel):
    reason: str
    details: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    thread_id: int
    reported_by: int
    reporter: Optional[AuthorInfo] = None
    reason: str
    details: Optional[str] = None
    status: str
    created_at: datetime
    thread_title: Optional[str] = None

    class Config:
        from_attributes = True


class ReportListPaginated(BaseModel):
    items: List[ReportResponse]
    total: int
