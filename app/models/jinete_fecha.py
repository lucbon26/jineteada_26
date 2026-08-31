
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JineteFecha(Base):
    __tablename__ = "jinete_fechas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    jinete_id: Mapped[int] = mapped_column(
        ForeignKey("jinetes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

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

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "jinete_id",
            "fecha_id",
            name="uq_jinete_fecha",
        ),
    )

    jinete = relationship("Jinete", back_populates="participaciones")
    fecha = relationship("Fecha")
    categoria = relationship("Categoria")
