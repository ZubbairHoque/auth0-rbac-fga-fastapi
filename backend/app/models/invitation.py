from datetime import datetime
from pydantic import BaseModel, Field

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
