from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campeonato import Campeonato
from app.models.fecha import Fecha
from app.models.sorteo import Sorteo


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Portal público"])


def campeonato_oficial_actual(db: Session) -> Campeonato | None:
    campeonatos = db.scalars(
        select(Campeonato)
        .where(Campeonato.modo_prueba == False)
        .order_by(Campeonato.id.desc())
    ).all()

    if not campeonatos:
        return None

    for campeonato in campeonatos:
        if str(campeonato.estado or "").lower() == "activo":
            return campeonato

    return campeonatos[0]


def proxima_fecha_oficial(
    campeonato: Campeonato | None,
    db: Session,
) -> Fecha | None:
    if campeonato is None:
        return None

    hoy = date.today()

    proxima = db.scalar(
        select(Fecha)
        .where(
            Fecha.campeonato_id == campeonato.id,
            Fecha.fecha >= hoy,
        )
        .order_by(Fecha.fecha.asc(), Fecha.id.asc())
    )
    if proxima is not None:
        return proxima

    return db.scalar(
        select(Fecha)
        .where(Fecha.campeonato_id == campeonato.id)
        .order_by(Fecha.fecha.desc(), Fecha.id.desc())
    )


def youtube_embed_url(url: str | None) -> str | None:
    """Convierte enlaces habituales de YouTube a una URL embed segura."""
    if not url:
        return None

    try:
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower().split(":")[0]
        path = parsed.path.strip("/")
        video_id = None

        if host in {"youtu.be", "www.youtu.be"}:
            video_id = path.split("/")[0] if path else None

        elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if path == "watch":
                video_id = parse_qs(parsed.query).get("v", [None])[0]
            elif path.startswith(("live/", "embed/", "shorts/")):
                parts = path.split("/")
                video_id = parts[1] if len(parts) > 1 else None

        if video_id and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id):
            return (
                f"https://www.youtube.com/embed/{video_id}"
                "?autoplay=1&mute=1&playsinline=1&rel=0"
            )

    except Exception:
        return None

    return None


@router.get("/", response_class=HTMLResponse)
def home_publico(
    request: Request,
    db: Session = Depends(get_db),
):
    campeonato = campeonato_oficial_actual(db)
    proxima_fecha = proxima_fecha_oficial(campeonato, db)

    youtube_url = None
    youtube_embed = None
    contador_objetivo = None

    if proxima_fecha is not None:
        contador_objetivo = (
            proxima_fecha.fecha.isoformat() + "T08:00:00-03:00"
        )

        if (
            proxima_fecha.youtube_publicar
            and proxima_fecha.youtube_url
        ):
            youtube_url = proxima_fecha.youtube_url
            youtube_embed = youtube_embed_url(youtube_url)

    cantidad_fechas = 0
    cantidad_sorteos_publicados = 0

    if campeonato is not None:
        cantidad_fechas = int(
            db.scalar(
                select(func.count(Fecha.id)).where(
                    Fecha.campeonato_id == campeonato.id
                )
            )
            or 0
        )

        cantidad_sorteos_publicados = int(
            db.scalar(
                select(func.count(Sorteo.id))
                .join(Fecha, Sorteo.fecha_id == Fecha.id)
                .where(
                    Fecha.campeonato_id == campeonato.id,
                    Sorteo.publicado == True,
                )
            )
            or 0
        )

    return templates.TemplateResponse(
        request=request,
        name="publico/home.html",
        context={
            "campeonato": campeonato,
            "proxima_fecha": proxima_fecha,
            "contador_objetivo": contador_objetivo,
            "youtube_url": youtube_url,
            "youtube_embed": youtube_embed,
            "cantidad_fechas": cantidad_fechas,
            "cantidad_sorteos_publicados": cantidad_sorteos_publicados,
            "menu_publico": "inicio",
        },
    )


@router.get("/campeonato", response_class=HTMLResponse)
def campeonato_publico(
    request: Request,
    db: Session = Depends(get_db),
):
    campeonato = campeonato_oficial_actual(db)

    fechas = []
    categorias = []
    if campeonato is not None:
        fechas = db.scalars(
            select(Fecha)
            .where(Fecha.campeonato_id == campeonato.id)
            .order_by(Fecha.fecha.asc(), Fecha.id.asc())
        ).all()
        categorias = list(campeonato.categorias or [])

    return templates.TemplateResponse(
        request=request,
        name="publico/campeonato.html",
        context={
            "campeonato": campeonato,
            "fechas": fechas,
            "categorias": categorias,
            "menu_publico": "campeonato",
        },
    )


@router.get("/resultados", response_class=HTMLResponse)
def resultados_publicos(
    request: Request,
    db: Session = Depends(get_db),
):
    campeonato = campeonato_oficial_actual(db)

    return templates.TemplateResponse(
        request=request,
        name="publico/resultados.html",
        context={
            "campeonato": campeonato,
            "menu_publico": "resultados",
        },
    )
