from sqlalchemy.orm import Session

from app.core.logger import logger
from app.core.security import hash_password
from app.models.usuario import Usuario


def crear_admin_inicial(db: Session) -> None:
    """
    Crea el usuario administrador inicial si la tabla usuarios está vacía.

    Esto permite iniciar el sistema por primera vez sin ejecutar scripts manuales.
    Luego, si ya existe al menos un usuario, no hace nada.
    """

    cantidad_usuarios = db.query(Usuario).count()

    if cantidad_usuarios > 0:
        return

    admin = Usuario(
        nombre="Administrador",
        usuario="admin",
        password_hash=hash_password("admin123"),
        rol="ADMIN",
        activo=True,
    )

    db.add(admin)
    db.commit()

    logger.info("Usuario administrador inicial creado: admin / admin123")