from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CaballoFecha(Base):
    """
    Relaciona un caballo con una fecha y una categoría.

    Permite definir qué caballos están disponibles para
    participar del sorteo de cada categoría en cada fecha.
    """

    __tablename__ = "caballos_fechas"

    __table_args__ = (
        UniqueConstraint(
            "caballo_id",
            "fecha_id",
            "categoria_id",
            name="uq_caballo_fecha_categoria",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    caballo_id: Mapped[int] = mapped_column(
        ForeignKey("caballos.id"),
        nullable=False,
        index=True,
    )

    fecha_id: Mapped[int] = mapped_column(
        ForeignKey("fechas.id"),
        nullable=False,
        index=True,
    )

    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id"),
        nullable=False,
        index=True,
    )

    caballo = relationship("Caballo")
    fecha = relationship("Fecha")
    categoria = relationship("Categoria")