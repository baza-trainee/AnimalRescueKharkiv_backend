import uuid

from sqlalchemy import UUID, String, UniqueConstraint
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.decl_api import DeclarativeMeta

Base: DeclarativeMeta = declarative_base()


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("entity", "operation", name="entity_operation_unique"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid1)
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
