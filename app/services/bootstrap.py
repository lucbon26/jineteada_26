from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.logger import logger
from app.core.permissions import MASTER_USUARIO
from app.core.security import hash_password
from app.models.usuario import Usuario


def crear_admin_inicial(db: Session) -> None:
    """Garantiza la existencia del usuario MASTER protegido del sistema."""
    master = db.query(Usuario).filter(Usuario.usuario == MASTER_USUARIO).first()

    if master:
        cambios = False
        if master.rol != "MASTER":
            master.rol = "MASTER"
            cambios = True
        if not master.activo:
            master.activo = True
            cambios = True
        if cambios:
            db.commit()
        return

    if not settings.MASTER_INITIAL_PASSWORD:
        raise RuntimeError(
            "No existe el usuario MASTER y falta configurar "
            "MASTER_INITIAL_PASSWORD en el entorno."
        )

    master = Usuario(
        nombre="Administrador",
        usuario=MASTER_USUARIO,
        password_hash=hash_password(settings.MASTER_INITIAL_PASSWORD),
        rol="MASTER",
        activo=True,
    )
    db.add(master)
    db.commit()
    logger.info("Usuario MASTER inicial creado")
