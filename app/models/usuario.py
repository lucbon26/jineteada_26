from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Usuario(Base):
    """
    Modelo de usuarios del sistema.

    Cada acción importante del sistema quedará asociada
    a un usuario para auditoría y transparencia.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="ADMIN")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)