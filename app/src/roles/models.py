import uuid

from sqlalchemy import UUID, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.orm.decl_api import DeclarativeMeta
from src.configuration.db import Base
from src.permissions.models import Permission

#Base: DeclarativeMeta = declarative_base()


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


class RolePermission(Base):
    __tablename__ = "roles_permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid1)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(Role.id, ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey(Permission.id), nullable=False)
