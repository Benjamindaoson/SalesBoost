from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserSchema(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str
    tenant_id: Optional[str] = None
