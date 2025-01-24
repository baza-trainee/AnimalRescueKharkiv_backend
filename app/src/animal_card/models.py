from uuid import uuid4

from sqlalchemy import UUID, Boolean, Date, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EmailType, PasswordType
from src.configuration.db import Base
from src.media.models import MediaAsset
from src.users.models import User


class AnimalCard(Base):
    __tablename__ = "animal_cards"
    # __table_args__ = (UniqueConstraint("email", "domain", name="email_domain_unique"),)
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, default=uuid4)
    animal_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    animal_name: Mapped[str] = mapped_column(String(50), index=False, nullable=False)

    animal_photo: Mapped[MediaAsset] = relationship(MediaAsset, lazy="joined")

    origin__arrival_date: Mapped[Date] = mapped_column(Date, default=func.now())
    origin__city: Mapped[str] = mapped_column(String(100), index=False, nullable=False)
    origin__address: Mapped[str] = mapped_column(String(100), index=False, nullable=True)

    general__animal_type: Mapped[str] = mapped_column(String(50), index=False, nullable=False)
    general__gender: Mapped[str] = mapped_column(String(10), index=False, nullable=False)
    general__weight: Mapped[float] = mapped_column(Float, index=False, nullable=True)
    general__age: Mapped[float] = mapped_column(Float, index=False, nullable=True)
    general__specials: Mapped[str] = mapped_column(String(200), index=False, nullable=True)

    location__current: Mapped[str] = mapped_column(String(100), index=False, nullable=False)
    location__from: Mapped[Date] = mapped_column(Date, default=func.now())
    location__to: Mapped[Date] = mapped_column(Date, default=func.now())
    # location__history: Mapped[str] = mapped_column(String(100), index=False, nullable=False)

    owner__info: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    comment__text: Mapped[str] = mapped_column(String(1000), index=False, nullable=True)

    adoption__country: Mapped[str] = mapped_column(String(50), index=False, nullable=True)
    adoption__city: Mapped[str] = mapped_column(String(50), index=False, nullable=True)
    adoption__date: Mapped[Date] = mapped_column(Date, default=func.now())
    adoption__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    death__date: Mapped[Date] = mapped_column(Date, default=func.now())
    death__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    sterilization__done: Mapped[bool] = mapped_column(Boolean, default=False, index=False, nullable=True)
    sterilization__date: Mapped[Date] = mapped_column(Date, default=func.now())
    sterilization__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    microchipping__done: Mapped[bool] = mapped_column(Boolean, default=False, index=False, nullable=True)
    microchipping__date: Mapped[Date] = mapped_column(Date, default=func.now())
    microchipping__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    vaccination__done: Mapped[bool] = mapped_column(Boolean, default=False, index=False, nullable=True)
    vaccination__type: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    vaccination__date: Mapped[Date] = mapped_column(Date, default=func.now())
    vaccination__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    diagnosis__name: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    diagnosis__date: Mapped[Date] = mapped_column(Date, default=func.now())
    diagnosis__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)

    procedure__name: Mapped[str] = mapped_column(String(100), index=False, nullable=True)
    procedure__date: Mapped[Date] = mapped_column(Date, default=func.now())
    procedure__comment: Mapped[str] = mapped_column(String(500), index=False, nullable=True)
