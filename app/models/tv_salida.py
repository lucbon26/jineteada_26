from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TvSalida(Base):
    """Estado único y configuración de la salida gráfica consumida por vMix."""

    __tablename__ = "tv_salidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    token: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True, index=True
    )

    escena: Mapped[str] = mapped_column(
        String(30), nullable=False, default="oculto"
    )

    sorteo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    detalle_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteo_detalles.id", ondelete="SET NULL"), nullable=True, index=True
    )

    tabla_pagina: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tabla_auto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ticker_cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=6)

    # Graph / lower third
    graph_color_principal: Mapped[str] = mapped_column(String(20), nullable=False, default="#00A651")
    graph_color_fondo: Mapped[str] = mapped_column(String(20), nullable=False, default="#101820")
    graph_color_texto: Mapped[str] = mapped_column(String(20), nullable=False, default="#FFFFFF")
    graph_color_secundario: Mapped[str] = mapped_column(String(20), nullable=False, default="#D9E2E8")
    graph_nombre_px: Mapped[int] = mapped_column(Integer, nullable=False, default=54)
    graph_detalle_px: Mapped[int] = mapped_column(Integer, nullable=False, default=31)
    graph_ancho_px: Mapped[int] = mapped_column(Integer, nullable=False, default=1280)
    graph_left_px: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    graph_bottom_px: Mapped[int] = mapped_column(Integer, nullable=False, default=72)

    # Ticker
    ticker_color_fondo: Mapped[str] = mapped_column(String(20), nullable=False, default="#101820")
    ticker_color_texto: Mapped[str] = mapped_column(String(20), nullable=False, default="#FFFFFF")
    ticker_color_acento: Mapped[str] = mapped_column(String(20), nullable=False, default="#00A651")
    ticker_fuente_px: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    ticker_alto_px: Mapped[int] = mapped_column(Integer, nullable=False, default=96)
    ticker_bottom_px: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    ticker_velocidad_seg: Mapped[int] = mapped_column(Integer, nullable=False, default=28)

    # Tabla de orden
    tabla_color_fondo: Mapped[str] = mapped_column(String(20), nullable=False, default="#101820")
    tabla_color_texto: Mapped[str] = mapped_column(String(20), nullable=False, default="#FFFFFF")
    tabla_color_acento: Mapped[str] = mapped_column(String(20), nullable=False, default="#00A651")
    tabla_fuente_px: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    tabla_filas: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    tabla_rotacion_seg: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sorteo = relationship("Sorteo")
    detalle = relationship("SorteoDetalle")
