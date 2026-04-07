from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class User(Base):
    """
    This class represents a 'User' in our database.
    It stores things like username, email, and what role they have.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="member") # Can be admin, moderator, or member
    name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    is_active = Column(Integer, default=1)  # 1 means active, 0 means banned/blocked
    created_at = Column(DateTime, default=func.now())
