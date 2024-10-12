import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID, Column, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.configuration.db import Base
from src.users.models import User


class TokenType(enum.Enum):
    access = 1
    invitation = 2
    reset = 3
    refresh = 4

class SecurityToken(Base):
    __tablename__ = "security_tokens"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    token: Mapped[str] = mapped_column(String(length=500), index=True)
    token_type = Column("token_type", Enum(TokenType), default=TokenType.access)
    created_at = Column("created_at", DateTime(timezone=True), default=func.now(), index=True)
    expire_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_id: Mapped[User] = mapped_column(ForeignKey(User.id, ondelete="cascade"), nullable=True)
    user: Mapped[User] = relationship(User, lazy="joined")
