from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    campeonato_id: Mapped[int] = mapped_column(
        ForeignKey("campeonatos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    puntua_campeonato: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    cantidad_montas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    tipo_monta: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    edad_minima: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    edad_maxima: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    peso_minimo: Mapped[float | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    peso_maximo: Mapped[float | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    reglamento: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    campeonato = relationship(
        "Campeonato",
        back_populates="categorias",
    )