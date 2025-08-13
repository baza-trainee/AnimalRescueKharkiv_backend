from uuid import uuid4

from sqlalchemy import UUID, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy_utils import EmailType, PasswordType
from src.configuration.db import Base
from src.media.models import MediaAsset
from src.roles.models import Role


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", "domain", name="email_domain_unique"),)
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    email: Mapped[EmailType] = mapped_column(EmailType(), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    password: Mapped[PasswordType] = mapped_column(PasswordType(schemes=["bcrypt"]), nullable=False)
    first_name: Mapped[str] = mapped_column(String(30), index=False, nullable=True)
    last_name: Mapped[str] = mapped_column(String(50), index=False, nullable=True)
    phone: Mapped[str] = mapped_column(String(30), index=False, unique=True, nullable=True)
    photo_id: Mapped[MediaAsset] = mapped_column(ForeignKey(MediaAsset.id, ondelete="SET NULL"),
                                                 index=True,
                                                 nullable=True)
    photo: Mapped[MediaAsset] = relationship(MediaAsset, lazy="joined")
    role_id: Mapped[Role] = mapped_column(ForeignKey(Role.id, ondelete="SET NULL"), index=True, nullable=True)
    role: Mapped[Role] = relationship(Role, back_populates="users", lazy="joined")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
