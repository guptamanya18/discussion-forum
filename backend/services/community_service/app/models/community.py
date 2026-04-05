import re
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a community name."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


class Community(Base):
    __tablename__="communities"

    id=Column(Integer,primary_key=True, index=True)
    name=Column(String, unique=True, index=True, nullable=False)
    slug=Column(String, unique=True, index=True, nullable=False)
    description=Column(Text,nullable=True)
    created_by=Column(Integer,ForeignKey("users.id"),nullable=False)
    created_at=Column(DateTime, default=func.now())

    creator=relationship("User")
    members=relationship("CommunityMember",back_populates="community",
                         cascade="all, delete-orphan", passive_deletes=True)