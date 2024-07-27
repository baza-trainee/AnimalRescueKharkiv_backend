import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.configuration.db import Base

if TYPE_CHECKING:
    from src.roles.models import Role


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("entity", "operation", name="entity_operation_unique"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid1)
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    roles: Mapped[list["Role"]] = relationship(secondary="roles_permissions",
                                                           back_populates="permissions",
                                                           lazy="joined")
