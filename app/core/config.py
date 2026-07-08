from pathlib import Path
from dotenv import load_dotenv
import os

# Carpeta raíz del proyecto.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carga variables desde archivo .env si existe.
load_dotenv(BASE_DIR / ".env")


class Settings:
    """
    Configuración central del sistema.

    Toda variable importante debe salir de acá para evitar valores
    desperdigados por el código.
    """

    APP_NAME: str = "Sistema de Gestión de Jineteadas"
    APP_VERSION: str = "0.1.0-dev"

    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DATA_DIR / 'jineteada.db'}"
    )


settings = Settings()

# Asegura que existan las carpetas necesarias.
settings.DATA_DIR.mkdir(exist_ok=True)
settings.LOGS_DIR.mkdir(exist_ok=True)