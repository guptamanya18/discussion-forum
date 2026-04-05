from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime, func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "thread_id", name="uq_like_user_thread"),
    )

    user = relationship("User")
    thread = relationship("Thread")
