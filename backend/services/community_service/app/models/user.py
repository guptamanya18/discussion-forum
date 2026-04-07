"""This file stores basic user info for the community service."""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class User(Base):
    __tablename__="users"

    id=Column(Integer, primary_key=True, index=True)
    username=Column(String, unique=True, index=True)
    email=Column(String, unique=True, index=True)
    hashed_password=Column(String)
    role=Column(String, default="member")
    bio=Column(String, nullable=True)
    avatar=Column(String, nullable=True)
    is_active=Column(Integer, default=1)
    created_at=Column(DateTime, default=func.now())

    