from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class RepechajeCategoria(Base):
    """Planilla independiente de F3; nunca aporta al acumulado del campeonato."""
    __tablename__ = 'repechajes_categorias'

    categoria_id: Mapped[int] = mapped_column(ForeignKey('categorias.id', ondelete='CASCADE'), primary_key=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default='borrador')
    base_firma: Mapped[str] = mapped_column(String(64), nullable=False)
    puntos_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    confirmado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmado_por: Mapped[str | None] = mapped_column(String(150), nullable=True)
