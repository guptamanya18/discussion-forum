from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.schemas.user import AuthorInfo


class ThreadCreate(BaseModel):
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    community_id: Optional[int] = None


class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class ThreadResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    tags: Optional[List[str]] = None
    status: str
    community_id: Optional[int] = None
    author: AuthorInfo
    created_at: datetime
    updated_at: datetime
    like_count: int = 0
    liked_by_me: bool = False
    reply_count: int = 0

    class Config:
        from_attributes = True


class ThreadList(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: str
    community_id: Optional[int] = None
    author: AuthorInfo
    created_at: datetime
    like_count: int = 0
    reply_count: int = 0


class ThreadListPaginated(BaseModel):
    items: List[ThreadList]
    total: int

    class Config:
        from_attributes = True