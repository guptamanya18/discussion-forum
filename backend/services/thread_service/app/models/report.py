"""This defines the information we store when someone reports a thread."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, dismissed
    created_at = Column(DateTime, default=func.now())

    thread = relationship("Thread")
    reporter = relationship("User")
