from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Campeonato(Base):
    """
    Campeonato general que agrupa fechas, categorías,
    inscripciones, sorteos y resultados.
    """

    __tablename__ = "campeonatos"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fecha_inicio: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    fecha_fin: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="borrador",
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
    )