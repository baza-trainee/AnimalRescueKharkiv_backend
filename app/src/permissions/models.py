import uuid

from sqlalchemy import UUID, Column, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.sql.sqltypes import DateTime

Base: DeclarativeMeta = declarative_base()

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    access_right: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
