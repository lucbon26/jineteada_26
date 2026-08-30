from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CaballoHistorial(Base):
    """Historial permanente de participaciones y estados del caballo."""

    __tablename__ = "caballos_historial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    caballo_id: Mapped[int] = mapped_column(
        ForeignKey("caballos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    campeonato_id: Mapped[int | None] = mapped_column(
        ForeignKey("campeonatos.id"),
        nullable=True,
        index=True,
    )

    fecha_id: Mapped[int | None] = mapped_column(
        ForeignKey("fechas.id"),
        nullable=True,
        index=True,
    )

    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id"),
        nullable=True,
        index=True,
    )

    evento: Mapped[str] = mapped_column(String(50), nullable=False)
    estado_caballo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    caballo = relationship("Caballo", back_populates="historial")
    campeonato = relationship("Campeonato")
    fecha = relationship("Fecha")
    categoria = relationship("Categoria")
