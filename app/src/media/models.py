import uuid

from sqlalchemy import UUID, Column, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import DateTime
from src.configuration.db import Base


class Blob(Base):
    __tablename__ = "blobs"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    blob_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    index: Mapped[int] = mapped_column(Integer, index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

class MediaAsset(Base):
    __tablename__ = "media_assets"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    blob_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    extension: Mapped[str] = mapped_column(String(15), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    updated_at = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
