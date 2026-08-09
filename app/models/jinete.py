from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Jinete(Base):
    __tablename__ = "jinetes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    nombres: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    apellidos: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    dni: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
    )

    fecha_nacimiento: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    sexo: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    nacionalidad: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
    )

    celular: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    provincia: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    localidad: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    categoria_habitual: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    club_agrupacion: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    observaciones: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="activo",
    )

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

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()