from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from datetime import UTC, datetime
from sqlalchemy import Boolean, Column, Enum,  String, DateTime
from app.core.database import Base

from app.modules.member.schema import MemberStatus

class MemberDB(Base):
    __tablename__ = "members"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    auth0_user_id: Mapped[str] = mapped_column(String, unique=True, nullable=True, index=True)
    role: Mapped[str ] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(Enum(MemberStatus), nullable=False, default=MemberStatus.invited, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

class InvitationDB(Base):
    __tablename__ = "Invitations"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True)
    role: Mapped[str] = mapped_column(String)
    token = Column(String)
    is_used: Mapped[bool] = mapped_column(Boolean)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
