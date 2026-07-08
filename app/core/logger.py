import logging
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_logger() -> logging.Logger:
    """
    Configura el logger principal del sistema.

    Guarda logs en archivo y también los muestra por consola.
    Esto ayuda a detectar errores durante el desarrollo y en uso real.
    """

    logger = logging.getLogger("jineteada")
    logger.setLevel(logging.INFO)

    # Evita duplicar logs si FastAPI recarga la app.
    if logger.handlers:
        return logger

    log_file = settings.LOGS_DIR / "sistema.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()