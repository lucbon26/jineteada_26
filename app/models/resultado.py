from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResultadoCategoria(Base):
    """Carga de resultados correspondiente a un sorteo oficial (Fecha + Categoría)."""

    __tablename__ = "resultados_categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sorteo_id: Mapped[int] = mapped_column(
        ForeignKey("sorteos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="borrador", index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    publicado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sorteo = relationship("Sorteo")
    detalles = relationship(
        "ResultadoDetalle",
        back_populates="resultado_categoria",
        cascade="all, delete-orphan",
    )


class ResultadoDetalle(Base):
    """Puntos y observaciones cargados para una fila del sorteo oficial."""

    __tablename__ = "resultados_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resultado_categoria_id: Mapped[int] = mapped_column(
        ForeignKey("resultados_categorias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sorteo_detalle_id: Mapped[int] = mapped_column(
        ForeignKey("sorteo_detalles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    puntos: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "resultado_categoria_id",
            "sorteo_detalle_id",
            name="uq_resultado_categoria_detalle",
        ),
    )

    resultado_categoria = relationship("ResultadoCategoria", back_populates="detalles")
    sorteo_detalle = relationship("SorteoDetalle")
