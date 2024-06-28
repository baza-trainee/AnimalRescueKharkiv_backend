import uuid
from sqlalchemy.orm import relationship, Mapped, mapped_column, backref, declarative_base
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy import UUID, Column, Integer, LargeBinary, String, Date, Boolean, func

Base = declarative_base()

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
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    content_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at = Column("created_at", DateTime, default=func.now(), index=True)
    updated_at = Column("updated_at", DateTime, default=func.now())
