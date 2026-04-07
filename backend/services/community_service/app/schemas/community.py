"""This defines the data format for creating and updating communities."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CommunityCreate(BaseModel):
    name:str
    description: Optional[str]=None

class CommunityUpdate(BaseModel):
    name:Optional[str]=None
    description: Optional[str]=None

class CommunityResponse(BaseModel):
    id:int
    name:str
    slug:str
    description:Optional[str]
    created_by:int
    created_at:datetime
    member_count:int=0

    class Config:
        from_attributes=True

class CommunityListPaginated(BaseModel):
    items: list[CommunityResponse]
    total: int


class MemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    avatar: Optional[str] = None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True

