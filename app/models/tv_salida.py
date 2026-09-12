from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TvSalida(Base):
    """Estado único y configuración de las salidas gráficas consumidas por vMix."""

    __tablename__ = "tv_salidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    token: Mapped[str] = mapped_column(
        String(80), nullable=False, unique=True, index=True
    )

    # Campos legacy de la primera versión. Se mantienen por compatibilidad.
    escena: Mapped[str] = mapped_column(
        String(30), nullable=False, default="oculto"
    )
    sorteo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    detalle_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteo_detalles.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Sorteo/contenido independiente por salida.
    graph_sorteo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ticker_sorteo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tabla_sorteo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    campeonato_sorteo_id: Mapped[int | None] = mapped_column(
        ForeignKey("sorteos.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Cada Browser Input tiene su estado propio. Nunca se encienden automáticamente.
    graph_al_aire: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ticker_al_aire: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tabla_sorteo_al_aire: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tabla_campeonato_al_aire: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    tabla_pagina: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tabla_auto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ticker_cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=6)

    # Graph: contenido visible y correcciones operativas exclusivas de TV.
    graph_mostrar_jinete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    graph_mostrar_localidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    graph_mostrar_caballo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    graph_mostrar_palenque: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    graph_mostrar_categoria: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    graph_override_palenque: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graph_override_caballo: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # JSON simple: {"<categoria_id>":[1,3], ...}. Solo afecta TV, nunca el sorteo.
    palenques_tv_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

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

    # Tabla de orden / campeonato
    tabla_color_fondo: Mapped[str] = mapped_column(String(20), nullable=False, default="#101820")
    tabla_color_texto: Mapped[str] = mapped_column(String(20), nullable=False, default="#FFFFFF")
    tabla_color_acento: Mapped[str] = mapped_column(String(20), nullable=False, default="#00A651")
    tabla_fuente_px: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    tabla_filas: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    tabla_rotacion_seg: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relaciones legacy.
    sorteo = relationship("Sorteo", foreign_keys=[sorteo_id])
    detalle = relationship("SorteoDetalle", foreign_keys=[detalle_id])

    graph_sorteo = relationship("Sorteo", foreign_keys=[graph_sorteo_id])
    ticker_sorteo = relationship("Sorteo", foreign_keys=[ticker_sorteo_id])
    tabla_sorteo = relationship("Sorteo", foreign_keys=[tabla_sorteo_id])
    campeonato_sorteo = relationship("Sorteo", foreign_keys=[campeonato_sorteo_id])
