from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logger import logger
from app.routers import auth, campeonatos
from app.services.bootstrap import crear_admin_inicial
from app.routers import fechas

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

app.add_middleware(
    SessionMiddleware,
    secret_key="cambiar-esta-clave-en-produccion"
)

app.include_router(auth.router)
app.include_router(campeonatos.router)
app.include_router(fechas.router)


templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup_event():
    """
    Evento que se ejecuta cuando inicia el sistema.
    Crea el usuario administrador inicial si todavía no existe.
    """

    logger.info("Sistema iniciado correctamente")
    logger.info("Base de datos conectada")

    db = SessionLocal()

    try:
        crear_admin_inicial(db)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """
    Dashboard principal protegido por sesión.
    """

    if not request.session.get("usuario_id"):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="dashboards.html",
        context={
            "menu_activo": "inicio",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )