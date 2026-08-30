from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CaballoFecha(Base):
    """
    Asignación vigente de un caballo.

    Un caballo puede tener una sola asignación activa a la vez.
    Las anteriores pasan al historial.
    """

    __tablename__ = "caballos_fechas"

    __table_args__ = (
        UniqueConstraint(
            "caballo_id",
            name="uq_caballo_asignacion_vigente",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

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
