from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Fecha(Base):
    __tablename__ = "fechas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    campeonato_id: Mapped[int] = mapped_column(
        ForeignKey("campeonatos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    localidad: Mapped[str] = mapped_column(String(100), nullable=False)
    provincia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lugar: Mapped[str | None] = mapped_column(String(150), nullable=True)
    organizador: Mapped[str | None] = mapped_column(String(150), nullable=True)

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="programada",
    )

    # El módulo Sorteos debe pasar este valor a True
    # cuando la fecha quede efectivamente sorteada.
    sorteada: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    campeonato = relationship(
        "Campeonato",
        back_populates="fechas",
    )
