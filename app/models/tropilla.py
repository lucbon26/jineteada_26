from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tropilla(Base):
    """
    Representa una tropilla registrada en el sistema.

    La tropilla se crea una sola vez y sus caballos pueden
    participar en distintas fechas del campeonato.
    """

    __tablename__ = "tropillas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )

    propietario: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    localidad: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    provincia: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    activo: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # Una tropilla puede contener muchos caballos.
    caballos = relationship(
        "Caballo",
        back_populates="tropilla",
    )