from __future__ import annotations

from datetime import datetime
import re
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import normalizar_rol
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.sorteo import Sorteo, SorteoDetalle
from app.models.tv_salida import TvSalida


templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/tv", tags=["TV"])

ESCENAS = {"oculto", "jinete", "tabla", "ticker", "posiciones"}
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFAULTS = {
    "graph_color_principal": "#00A651",
    "graph_color_fondo": "#101820",
    "graph_color_texto": "#FFFFFF",
    "graph_color_secundario": "#D9E2E8",
    "graph_nombre_px": 54,
    "graph_detalle_px": 31,
    "graph_ancho_px": 1280,
    "graph_left_px": 64,
    "graph_bottom_px": 72,
    "ticker_color_fondo": "#101820",
    "ticker_color_texto": "#FFFFFF",
    "ticker_color_acento": "#00A651",
    "ticker_fuente_px": 30,
    "ticker_alto_px": 96,
    "ticker_bottom_px": 48,
    "ticker_velocidad_seg": 28,
    "tabla_color_fondo": "#101820",
    "tabla_color_texto": "#FFFFFF",
    "tabla_color_acento": "#00A651",
    "tabla_fuente_px": 30,
    "tabla_filas": 8,
    "tabla_rotacion_seg": 8,
}


def exigir_operador_tv(request: Request) -> None:
    rol = normalizar_rol(request.session.get("usuario_rol"))
    if rol not in {"MASTER", "TV"}:
        raise HTTPException(status_code=403, detail="Acceso exclusivo para TV y MASTER.")


def obtener_o_crear_salida(db: Session) -> TvSalida:
    salida = db.scalar(select(TvSalida).order_by(TvSalida.id.asc()))
    if salida is None:
        salida = TvSalida(token=secrets.token_urlsafe(32), escena="oculto")
        db.add(salida)
        db.commit()
        db.refresh(salida)
    return salida


def detalles_utiles(sorteo: Sorteo | None) -> list[SorteoDetalle]:
    if sorteo is None:
        return []
    return [d for d in sorteo.detalles if not d.es_reserva and d.jinete_id is not None]


def detalle_valido(sorteo: Sorteo | None, detalle_id: int | None) -> SorteoDetalle | None:
    if sorteo is None or detalle_id is None:
        return None
    return next((d for d in detalles_utiles(sorteo) if d.id == detalle_id), None)


def serializar_detalle(detalle: SorteoDetalle, categoria: str | None = None) -> dict:
    return {
        "id": detalle.id,
        "orden": detalle.orden,
        "palenque": detalle.palenque,
        "jinete": detalle.jinete_nombre or "-",
        "localidad": detalle.jinete_localidad or "-",
        "caballo": detalle.caballo_nombre or "-",
        "tropilla": detalle.tropilla_nombre or "-",
        "categoria": categoria or "-",
    }


def contexto_seleccion(db: Session, campeonato_id: int | None, fecha_id: int | None, categoria_id: int | None):
    campeonatos = db.scalars(
        select(Campeonato)
        .join(Fecha, Fecha.campeonato_id == Campeonato.id)
        .join(Sorteo, Sorteo.fecha_id == Fecha.id)
        .distinct()
        .order_by(Campeonato.fecha_inicio.desc(), Campeonato.id.desc())
    ).all()

    if campeonato_id is None and campeonatos:
        campeonato_id = campeonatos[0].id

    fechas = []
    if campeonato_id is not None:
        fechas = db.scalars(
            select(Fecha)
            .join(Sorteo, Sorteo.fecha_id == Fecha.id)
            .where(Fecha.campeonato_id == campeonato_id)
            .distinct()
            .order_by(Fecha.fecha.asc(), Fecha.id.asc())
        ).all()

    ids_fechas = {f.id for f in fechas}
    if fecha_id not in ids_fechas:
        fecha_id = fechas[0].id if fechas else None

    categorias = []
    if fecha_id is not None:
        categorias = db.scalars(
            select(Categoria)
            .join(Sorteo, Sorteo.categoria_id == Categoria.id)
            .where(Sorteo.fecha_id == fecha_id)
            .distinct()
            .order_by(Categoria.orden.asc(), Categoria.nombre.asc())
        ).all()

    ids_categorias = {c.id for c in categorias}
    if categoria_id not in ids_categorias:
        categoria_id = categorias[0].id if categorias else None

    sorteo = None
    if fecha_id is not None and categoria_id is not None:
        sorteo = db.scalar(
            select(Sorteo).where(Sorteo.fecha_id == fecha_id, Sorteo.categoria_id == categoria_id)
        )

    return campeonatos, fechas, categorias, sorteo, campeonato_id, fecha_id, categoria_id


def color(valor: str, defecto: str) -> str:
    valor = (valor or "").strip()
    return valor.upper() if HEX_RE.match(valor) else defecto


def entero(valor: int, minimo: int, maximo: int, defecto: int) -> int:
    try:
        return min(maximo, max(minimo, int(valor)))
    except (TypeError, ValueError):
        return defecto


@router.get("", response_class=HTMLResponse)
def panel_tv(request: Request, campeonato_id: int | None = Query(default=None), fecha_id: int | None = Query(default=None), categoria_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    campeonatos, fechas, categorias, sorteo, campeonato_id, fecha_id, categoria_id = contexto_seleccion(db, campeonato_id, fecha_id, categoria_id)
    detalles = detalles_utiles(sorteo)
    seleccionado = detalle_valido(sorteo, salida.detalle_id)
    if seleccionado is None and detalles:
        seleccionado = detalles[0]

    return templates.TemplateResponse(
        request=request,
        name="tv/panel.html",
        context={
            "menu_activo": "tv",
            "usuario_nombre": request.session.get("usuario_nombre", "TV"),
            "salida": salida,
            "salida_url": str(request.base_url).rstrip("/") + f"/tv/salida/{salida.token}",
            "campeonatos": campeonatos,
            "fechas": fechas,
            "categorias": categorias,
            "campeonato_id": campeonato_id,
            "fecha_id": fecha_id,
            "categoria_id": categoria_id,
            "sorteo": sorteo,
            "detalles": detalles,
            "seleccionado": seleccionado,
        },
    )


@router.post("/salida/actualizar")
def actualizar_salida(request: Request, escena: str = Form(...), sorteo_id: int | None = Form(default=None), detalle_id: int | None = Form(default=None), tabla_pagina: int = Form(default=1), tabla_auto: str | None = Form(default=None), ticker_cantidad: int = Form(default=6), db: Session = Depends(get_db)):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    escena = escena.strip().lower()
    if escena not in ESCENAS:
        raise HTTPException(status_code=400, detail="Escena TV inválida.")

    if escena == "oculto":
        salida.escena = "oculto"
        salida.actualizado_en = datetime.utcnow()
        db.commit()
        request.session["flash_success"] = "Salida TV oculta."
        return RedirectResponse("/tv", status_code=303)

    if sorteo_id is None:
        raise HTTPException(status_code=400, detail="Seleccioná un sorteo antes de enviar una gráfica.")
    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado.")

    if escena == "jinete":
        detalle = db.get(SorteoDetalle, detalle_id) if detalle_id else None
        if detalle is None or detalle.sorteo_id != sorteo.id or detalle.es_reserva:
            raise HTTPException(status_code=400, detail="Seleccioná un jinete válido del sorteo.")
        salida.detalle_id = detalle.id
    elif detalle_id:
        detalle = db.get(SorteoDetalle, detalle_id)
        if detalle is not None and detalle.sorteo_id == sorteo.id and not detalle.es_reserva:
            salida.detalle_id = detalle.id

    salida.sorteo_id = sorteo.id
    salida.escena = escena
    salida.tabla_pagina = max(1, tabla_pagina)
    salida.tabla_auto = tabla_auto == "on"
    salida.ticker_cantidad = min(20, max(1, ticker_cantidad))
    salida.actualizado_en = datetime.utcnow()
    db.commit()

    request.session["flash_success"] = "Gráfica enviada a la salida TV."
    return RedirectResponse(f"/tv?campeonato_id={sorteo.fecha.campeonato_id}&fecha_id={sorteo.fecha_id}&categoria_id={sorteo.categoria_id}", status_code=303)


@router.post("/configuracion")
def guardar_configuracion(
    request: Request,
    graph_color_principal: str = Form(...), graph_color_fondo: str = Form(...), graph_color_texto: str = Form(...), graph_color_secundario: str = Form(...),
    graph_nombre_px: int = Form(...), graph_detalle_px: int = Form(...), graph_ancho_px: int = Form(...), graph_left_px: int = Form(...), graph_bottom_px: int = Form(...),
    ticker_color_fondo: str = Form(...), ticker_color_texto: str = Form(...), ticker_color_acento: str = Form(...), ticker_fuente_px: int = Form(...), ticker_alto_px: int = Form(...), ticker_bottom_px: int = Form(...), ticker_velocidad_seg: int = Form(...),
    tabla_color_fondo: str = Form(...), tabla_color_texto: str = Form(...), tabla_color_acento: str = Form(...), tabla_fuente_px: int = Form(...), tabla_filas: int = Form(...), tabla_rotacion_seg: int = Form(...),
    campeonato_id: int | None = Form(default=None), fecha_id: int | None = Form(default=None), categoria_id: int | None = Form(default=None), db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)

    salida.graph_color_principal = color(graph_color_principal, DEFAULTS["graph_color_principal"])
    salida.graph_color_fondo = color(graph_color_fondo, DEFAULTS["graph_color_fondo"])
    salida.graph_color_texto = color(graph_color_texto, DEFAULTS["graph_color_texto"])
    salida.graph_color_secundario = color(graph_color_secundario, DEFAULTS["graph_color_secundario"])
    salida.graph_nombre_px = entero(graph_nombre_px, 28, 90, DEFAULTS["graph_nombre_px"])
    salida.graph_detalle_px = entero(graph_detalle_px, 18, 60, DEFAULTS["graph_detalle_px"])
    salida.graph_ancho_px = entero(graph_ancho_px, 700, 1750, DEFAULTS["graph_ancho_px"])
    salida.graph_left_px = entero(graph_left_px, 0, 1100, DEFAULTS["graph_left_px"])
    salida.graph_bottom_px = entero(graph_bottom_px, 0, 700, DEFAULTS["graph_bottom_px"])

    salida.ticker_color_fondo = color(ticker_color_fondo, DEFAULTS["ticker_color_fondo"])
    salida.ticker_color_texto = color(ticker_color_texto, DEFAULTS["ticker_color_texto"])
    salida.ticker_color_acento = color(ticker_color_acento, DEFAULTS["ticker_color_acento"])
    salida.ticker_fuente_px = entero(ticker_fuente_px, 18, 56, DEFAULTS["ticker_fuente_px"])
    salida.ticker_alto_px = entero(ticker_alto_px, 60, 180, DEFAULTS["ticker_alto_px"])
    salida.ticker_bottom_px = entero(ticker_bottom_px, 0, 500, DEFAULTS["ticker_bottom_px"])
    salida.ticker_velocidad_seg = entero(ticker_velocidad_seg, 6, 120, DEFAULTS["ticker_velocidad_seg"])

    salida.tabla_color_fondo = color(tabla_color_fondo, DEFAULTS["tabla_color_fondo"])
    salida.tabla_color_texto = color(tabla_color_texto, DEFAULTS["tabla_color_texto"])
    salida.tabla_color_acento = color(tabla_color_acento, DEFAULTS["tabla_color_acento"])
    salida.tabla_fuente_px = entero(tabla_fuente_px, 18, 48, DEFAULTS["tabla_fuente_px"])
    salida.tabla_filas = entero(tabla_filas, 4, 12, DEFAULTS["tabla_filas"])
    salida.tabla_rotacion_seg = entero(tabla_rotacion_seg, 3, 60, DEFAULTS["tabla_rotacion_seg"])
    salida.actualizado_en = datetime.utcnow()
    db.commit()

    request.session["flash_success"] = "Configuración gráfica TV guardada."
    url = "/tv"
    if campeonato_id:
        url += f"?campeonato_id={campeonato_id}"
        if fecha_id:
            url += f"&fecha_id={fecha_id}"
        if categoria_id:
            url += f"&categoria_id={categoria_id}"
    return RedirectResponse(url, status_code=303)


@router.post("/configuracion/restaurar")
def restaurar_configuracion(request: Request, db: Session = Depends(get_db)):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    for campo, valor in DEFAULTS.items():
        setattr(salida, campo, valor)
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = "Diseño TV restaurado a valores predeterminados."
    return RedirectResponse("/tv", status_code=303)


@router.post("/salida/regenerar-token")
def regenerar_token(request: Request, db: Session = Depends(get_db)):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    salida.token = secrets.token_urlsafe(32)
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = "URL TV regenerada. La URL anterior quedó invalidada."
    return RedirectResponse("/tv", status_code=303)


@router.get("/salida/{token}", response_class=HTMLResponse)
def salida_vmix(request: Request, token: str, db: Session = Depends(get_db)):
    salida = db.scalar(select(TvSalida).where(TvSalida.token == token))
    if salida is None:
        raise HTTPException(status_code=404, detail="Salida TV no encontrada.")
    return templates.TemplateResponse(request=request, name="tv/salida.html", context={"token": token}, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/salida/{token}/estado", response_class=JSONResponse)
def estado_salida_vmix(token: str, db: Session = Depends(get_db)):
    salida = db.scalar(select(TvSalida).where(TvSalida.token == token))
    if salida is None:
        raise HTTPException(status_code=404, detail="Salida TV no encontrada.")

    sorteo = db.get(Sorteo, salida.sorteo_id) if salida.sorteo_id else None
    detalles = detalles_utiles(sorteo)
    actual = detalle_valido(sorteo, salida.detalle_id)
    categoria = sorteo.categoria if sorteo is not None else None
    categoria_nombre = categoria.nombre if categoria else None

    indice_actual = 0
    if actual is not None:
        for i, detalle in enumerate(detalles):
            if detalle.id == actual.id:
                indice_actual = i
                break

    siguientes = detalles[indice_actual + 1: indice_actual + 1 + salida.ticker_cantidad] if actual is not None else detalles[: salida.ticker_cantidad]
    fecha = sorteo.fecha if sorteo is not None else None

    configuracion = {campo: getattr(salida, campo) for campo in DEFAULTS}

    return JSONResponse(
        content={
            "escena": salida.escena,
            "actualizado_en": salida.actualizado_en.isoformat() if salida.actualizado_en else None,
            "campeonato": fecha.campeonato.nombre if fecha else None,
            "fecha": fecha.nombre if fecha else None,
            "fecha_id": fecha.id if fecha else None,
            "categoria": categoria_nombre,
            "actual": serializar_detalle(actual, categoria_nombre) if actual else None,
            "detalles": [serializar_detalle(d, categoria_nombre) for d in detalles],
            "siguientes": [serializar_detalle(d, categoria_nombre) for d in siguientes],
            "tabla_pagina": salida.tabla_pagina,
            "tabla_auto": salida.tabla_auto,
            "filas_por_pagina": salida.tabla_filas,
            "ticker_cantidad": salida.ticker_cantidad,
            "config": configuracion,
            "posiciones": [],
            "posiciones_disponibles": False,
        },
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "X-Robots-Tag": "noindex, nofollow, noarchive"},
    )
