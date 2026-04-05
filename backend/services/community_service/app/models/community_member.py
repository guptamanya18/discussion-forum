from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base

class CommunityMember(Base):
    __tablename__="community_members"

    id=Column(Integer, primary_key=True, index=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    community_id=Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"),
                        nullable=False)
    role=Column(String,default="member")
    joined_at=Column(DateTime,default=func.now())

    community=relationship("Community",back_populates="members")
    user=relationship("User")

    __table_args__=(
        UniqueConstraint("user_id","community_id",name="uq_user_community"),
    )

    