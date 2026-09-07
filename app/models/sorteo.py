from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Sorteo(Base):
    __tablename__ = "sorteos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    fecha_id: Mapped[int] = mapped_column(
        ForeignKey("fechas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # cantidad total de caballos que quedaron dentro del sorteo:
    # jinetes validados + reservas elegidas
    cantidad_caballos_sorteados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    cantidad_reservas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )

    publicado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    sorteado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    sorteado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    sorteado_por_nombre: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    publicado_en: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "fecha_id",
            "categoria_id",
            name="uq_sorteo_fecha_categoria",
        ),
    )

    fecha = relationship("Fecha")
    categoria = relationship("Categoria")
    detalles = relationship(
        "SorteoDetalle",
        back_populates="sorteo",
        cascade="all, delete-orphan",
        order_by="SorteoDetalle.orden",
    )


class SorteoDetalle(Base):
    __tablename__ = "sorteo_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    sorteo_id: Mapped[int] = mapped_column(
        ForeignKey("sorteos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Los registros de reserva no tienen jinete.
    jinete_id: Mapped[int | None] = mapped_column(
        ForeignKey("jinetes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    caballo_id: Mapped[int] = mapped_column(
        ForeignKey("caballos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    palenque: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    es_reserva: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # Copias de lectura para preservar el resultado tal como fue sorteado.
    jinete_nombre: Mapped[str | None] = mapped_column(
        String(220),
        nullable=True,
    )
    jinete_localidad: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )
    caballo_nombre: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )
    tropilla_nombre: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    sorteo = relationship("Sorteo", back_populates="detalles")
    jinete = relationship("Jinete")
    caballo = relationship("Caballo")
