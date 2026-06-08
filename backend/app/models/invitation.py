from datetime import datetime

from pydantic import BaseModel


class InvitationBase(BaseModel):
    email: str
    role: str  # 'admin' or 'member' 

class InvitationCreate(InvitationBase):
    pass

class InviateUpdate(BaseModel):
    email: str
    role: str
    token: str

class Invitation(InvitationBase):
    id: str
    token: str
    is_used: bool = False
    created_at: datetime

class Auth0RegistrationPayLoad(BaseModel):
    user_id: str
    email: str
