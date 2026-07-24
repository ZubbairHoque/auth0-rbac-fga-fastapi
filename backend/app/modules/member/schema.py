from sqlalchemy.orm import mapped_column
from datetime import datetime
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin", "member"]

class MemberBase(BaseModel):
    email: str = Field(..., min_length=3)
    role: Role  

class MemberStatus(StrEnum):
    invited = "invited"
    active = "active"
    removed = "removed"


class MemberCreate(MemberBase):
    pass


class Member(MemberBase):
    id: str
    auth0_user_id: Optional[str] = None
    status: MemberStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvitationBase(BaseModel):
    email: str
    role: str

class InvitationCreate(InvitationBase):
    """Schema for creating a new invitation (Input)."""
    pass

class Invitation(InvitationBase):
    """Schema for a full invitation record (Output)."""
    id: str
    token: str
    is_used: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class Auth0RegistrationPayLoad(BaseModel):
    """Schema for the Auth0 Post-Registration webhook payload."""
    user_id: str
    email: str