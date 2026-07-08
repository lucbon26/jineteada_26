from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """
    Clase base para todos los modelos de SQLAlchemy.

    Todas las tablas del sistema van a heredar de esta clase.
    """
    pass


# Engine principal de base de datos.
# Por ahora usamos SQLite local.
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Fábrica de sesiones.
# Cada operación contra la base usa una sesión.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """
    Dependencia para obtener una sesión de base de datos.

    FastAPI la usará en routers y servicios.
    Cierra automáticamente la conexión al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()