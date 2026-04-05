from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class NotificationEmit(BaseModel):
    user_id: int
    type: str
    message: str
    reference_id: Optional[int] = None


class NotificationResponse(BaseModel):
    id: int
    type: str
    message: str
    reference_id: Optional[int]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListPaginated(BaseModel):
    items: list[NotificationResponse]
    total: int


class UnreadCount(BaseModel):
    count: int
