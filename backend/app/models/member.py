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
