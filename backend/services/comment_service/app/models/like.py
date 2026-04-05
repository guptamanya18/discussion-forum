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
    comment_id = Column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="uq_like_user_comment"),
    )

    user = relationship("User")
    comment = relationship("Comment")
