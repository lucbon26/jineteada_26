from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SorteoAuditoria(Base):
    __tablename__ = "sorteo_auditoria"

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

    evento: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    usuario_nombre: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    detalle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
