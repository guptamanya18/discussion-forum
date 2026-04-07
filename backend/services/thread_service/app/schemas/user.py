"""This defines the user information format used in this service."""
from pydantic import BaseModel
from typing import Optional


class AuthorInfo(BaseModel):
    id: int
    username: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True
