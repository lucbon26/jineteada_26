from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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

    # pendiente | validado | ausente | no_habilitado
    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendiente",
        index=True,
    )

    motivo_no_habilitado: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    validado_en: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    validado_por: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    @property
    def habilitado_sorteo(self) -> bool:
        return self.estado == "validado"
