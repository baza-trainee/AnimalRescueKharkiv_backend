from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class TokenBase(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmailBase(BaseModel):
    email: EmailStr


class EmailInvite(EmailBase):
    role: str
    language: Optional[str] = "ua"

    model_config = ConfigDict(from_attributes=True)


class EmailRegistr(EmailBase):
    username: str


class UserInvite(BaseModel):
    email: EmailStr
    role: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
