"""This file defines the format for like-related data sent over the internet."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LikeResponse(BaseModel):
    id: int
    user_id: int
    thread_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LikeUserResponse(BaseModel):
    id: int
    username: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True
