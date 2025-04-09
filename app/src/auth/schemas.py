from typing import Optional

from pydantic import BaseModel, ConfigDict
from src.auth.models import TokenType
from src.users.schemas import ExtEmailStr, PwdStr


class TokenBase(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmailBase(BaseModel):
    email: ExtEmailStr


class EmailInvite(EmailBase):
    role: str
    language: Optional[str] = "ua"

    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    email: ExtEmailStr
    password: PwdStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class TokenValidate(BaseModel):
    token: str
    token_type: Optional[TokenType] = TokenType.reset
