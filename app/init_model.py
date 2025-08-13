from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from src.configuration.db import Base


class InitData(Base):
    __tablename__ = "init_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_hash: Mapped[str] = mapped_column(String(65), index=False, nullable=False)
