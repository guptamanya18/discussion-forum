"""This defines what a notification message looks like in the database."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    reference_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
