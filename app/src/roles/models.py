import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.configuration.db import Base
from src.permissions.models import Permission

if TYPE_CHECKING:
    from src.users.models import User


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("name", "domain", name="name_domain_unique"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid1)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    permissions: Mapped[list["Permission"]] = relationship(secondary="roles_permissions",
                                                           back_populates="roles",
                                                           lazy="joined")
    users: Mapped[list["User"]] = relationship("User", back_populates="role", lazy="joined")


class RolePermission(Base):
    __tablename__ = "roles_permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid1)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(Role.id, ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey(Permission.id), nullable=False)
