from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.schemas.user import AuthorInfo


class CommentCreate(BaseModel):
    content: str
    thread_id: int
    parent_comment_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    content: str
    thread_id: int
    author: AuthorInfo
    parent_comment_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentList(BaseModel):
    id: int
    content: str
    thread_id: int
    author: AuthorInfo
    parent_comment_id: Optional[int] = None
    created_at: datetime
    like_count: int = 0

    class Config:
        from_attributes = True


class CommentTree(BaseModel):
    id: int
    content: str
    thread_id: int
    author: AuthorInfo
    parent_comment_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    like_count: int = 0
    liked_by_me: bool = False
    reply_count: int = 0
    replies: List[CommentTree] = Field(default_factory=list)

    class Config:
        from_attributes = True


CommentTree.model_rebuild()
