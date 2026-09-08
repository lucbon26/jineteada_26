from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logger import logger
from app.routers import auth, campeonatos, usuarios
from app.services.bootstrap import crear_admin_inicial
from app.core.permissions import acceso_permitido, destino_por_rol
from app.routers import fechas
from app.routers import categorias
from app.routers import jinetes
from app.routers import tropillas
from app.routers import caballos
from app.routers import caballos_fechas
from app.routers import publico as publico_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(campeonatos.router)
app.include_router(fechas.router)
app.include_router(categorias.router)
app.include_router(jinetes.router)
app.include_router(tropillas.router)
app.include_router(caballos.router)
app.include_router(caballos_fechas.router)
app.include_router(publico_router.router)


templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(HTTPException)
async def manejar_http_exception(request: Request, exc: HTTPException):
    """
    En navegación HTML vuelve a la pantalla anterior y muestra un aviso
    flotante. Las llamadas fetch/API siguen recibiendo JSON.
    """
    accept = request.headers.get("accept", "")
    es_navegacion_html = "text/html" in accept

    if not es_navegacion_html:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    mensaje = exc.detail if isinstance(exc.detail, str) else "Ocurrió un error."
    request.session["flash_error"] = mensaje

    referer = request.headers.get("referer")
    if referer and referer.startswith(str(request.base_url).rstrip("/")):
        destino = referer
    else:
        destino = "/"

    return RedirectResponse(destino, status_code=303)


@app.middleware("http")
async def control_accesos(request: Request, call_next):
    request.state.flash_error = request.session.pop("flash_error", None)
    request.state.flash_success = request.session.pop("flash_success", None)
    path = request.url.path

    rutas_publicas = {"/", "/campeonato", "/resultados", "/login"}
    if (
        path in rutas_publicas
        or path.startswith("/publico/sorteos")
        or path.startswith("/static/")
    ):
        return await call_next(request)

    # /panel conserva el dashboard administrativo anterior.
    if path == "/panel":
        if not request.session.get("usuario_id"):
            return RedirectResponse("/login?next=/panel", status_code=303)
        return await call_next(request)

    if acceso_permitido(request):
        return await call_next(request)

    if not request.session.get("usuario_id"):
        if path != "/login":
            return RedirectResponse(f"/login?next={path}", status_code=303)
        return await call_next(request)

    return PlainTextResponse("No tenés permisos para acceder a esta sección.", status_code=403)

# SessionMiddleware debe quedar por fuera del middleware de permisos
# para que request.session exista cuando se evalúa el acceso.
app.add_middleware(
    SessionMiddleware,
    secret_key="cambiar-esta-clave-en-produccion"
)


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


@app.get("/panel", response_class=HTMLResponse)
def dashboard(request: Request):
    """
    Dashboard principal protegido por sesión.
    """

    if not request.session.get("usuario_id"):
        return RedirectResponse("/login", status_code=303)

    destino = destino_por_rol(request.session.get("usuario_rol"))
    if destino != "/":
        return RedirectResponse(destino, status_code=303)

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
# MODULO7_INSCRIPCIONES
from app.routers import inscripciones as inscripciones_router
app.include_router(inscripciones_router.router)

# MODULO7_ACREDITACION
from app.routers import acreditacion as acreditacion_router
app.include_router(acreditacion_router.router)

# MODULO8_SORTEOS
from app.routers import sorteos as sorteos_router
app.include_router(sorteos_router.router)
app.include_router(sorteos_router.public_router)
