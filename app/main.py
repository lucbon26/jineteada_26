from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.database import Base, engine
from app.core.logger import logger


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION
)

templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup_event():
    logger.info("Sistema iniciado correctamente")
    logger.info("Base de datos conectada")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    context = {
        "request": request,
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database_status": "Conectada",
        "logger_status": "Iniciado",
        "api_status": "Funcionando",
    }

    return templates.TemplateResponse(
         request,
        "dashboards.html",
        context
    )