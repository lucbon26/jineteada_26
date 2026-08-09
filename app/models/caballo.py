from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Caballo(Base):
    """
    Padrón único de caballos.

    Un caballo se registra una sola vez y puede aparecer
    nuevamente en diferentes fechas.
    """

    __tablename__ = "caballos"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    tropilla_id: Mapped[int | None] = mapped_column(
        ForeignKey("tropillas.id"),
        nullable=True,
        index=True,
    )

    pelaje: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="activo",
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    tropilla = relationship(
        "Tropilla",
        back_populates="caballos",
    )