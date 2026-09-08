from __future__ import annotations

from datetime import date

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


@router.get("/", response_class=HTMLResponse)
def home_publico(
    request: Request,
    db: Session = Depends(get_db),
):
    # Mantiene el flujo actual del login: si un usuario ya inició sesión,
    # "/" lo lleva al panel interno.
    if request.session.get("usuario_id"):
        return RedirectResponse("/panel", status_code=303)

    campeonato = campeonato_oficial_actual(db)
    proxima_fecha = proxima_fecha_oficial(campeonato, db)

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
