
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JineteCampeonato(Base):
    __tablename__ = "jinete_campeonatos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    jinete_id: Mapped[int] = mapped_column(
        ForeignKey("jinetes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    campeonato_id: Mapped[int] = mapped_column(
        ForeignKey("campeonatos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categorias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    estado_clasificacion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    causa_clasificacion: Mapped[str | None] = mapped_column(String(60), nullable=True)
    categoria_clasificacion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "jinete_id",
            "campeonato_id",
            name="uq_jinete_campeonato",
        ),
    )

    jinete = relationship("Jinete", back_populates="campeonatos")
    campeonato = relationship("Campeonato")
    categoria = relationship("Categoria")
