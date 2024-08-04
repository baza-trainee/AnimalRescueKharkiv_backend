from uuid import uuid1

from sqlalchemy import UUID, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EmailType, PasswordType
from src.configuration.db import Base
from src.roles.models import Role


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", "domain", name="username_domain_unique"),
        UniqueConstraint("email", "domain", name="email_domain_unique"),
    )
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid1)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[EmailType] = mapped_column(EmailType(), nullable=False)
    domain: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    password: Mapped[PasswordType] = mapped_column(PasswordType(schemes=["bcrypt"]), nullable=False)
    role_id: Mapped[Role] = mapped_column(ForeignKey(Role.id, ondelete="SET NULL"), nullable=True)
    role: Mapped[Role] = relationship(Role, back_populates="users", lazy="joined")
