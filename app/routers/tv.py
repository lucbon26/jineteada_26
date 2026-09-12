from __future__ import annotations

from datetime import datetime
import json
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
from app.services.resultados import posiciones_campeonato


templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/tv", tags=["TV"])

TIPOS_SALIDA = {"graph", "ticker", "sorteo", "campeonato"}
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
    return sorted(
        [d for d in sorteo.detalles if not d.es_reserva and d.jinete_id is not None],
        key=lambda d: (d.orden or 0, d.id),
    )


def detalle_valido(sorteo: Sorteo | None, detalle_id: int | None) -> SorteoDetalle | None:
    if sorteo is None or detalle_id is None:
        return None
    return next((d for d in detalles_utiles(sorteo) if d.id == detalle_id), None)


def cargar_palenques_config(salida: TvSalida) -> dict[str, list[int]]:
    try:
        raw = json.loads(salida.palenques_tv_json or "{}")
        if not isinstance(raw, dict):
            return {}
        limpio: dict[str, list[int]] = {}
        for clave, valores in raw.items():
            if not isinstance(valores, list):
                continue
            activos = sorted({int(v) for v in valores if int(v) in {1, 2, 3}})
            limpio[str(clave)] = activos or [1, 2, 3]
        return limpio
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def palenques_activos(salida: TvSalida, categoria_id: int | None) -> list[int]:
    if categoria_id is None:
        return [1, 2, 3]
    return cargar_palenques_config(salida).get(str(categoria_id), [1, 2, 3])


def guardar_palenques_activos(salida: TvSalida, categoria_id: int, activos: list[int]) -> None:
    config = cargar_palenques_config(salida)
    config[str(categoria_id)] = sorted({p for p in activos if p in {1, 2, 3}}) or [1, 2, 3]
    salida.palenques_tv_json = json.dumps(config, separators=(",", ":"))


def palenque_tv_automatico(detalle: SorteoDetalle, detalles: list[SorteoDetalle], activos: list[int]) -> int | str | None:
    if not activos:
        return detalle.palenque
    if activos == [1, 2, 3]:
        return detalle.palenque
    try:
        indice = next(i for i, d in enumerate(detalles) if d.id == detalle.id)
    except StopIteration:
        return detalle.palenque
    return activos[indice % len(activos)]


def serializar_detalle(
    detalle: SorteoDetalle,
    categoria: str | None = None,
    *,
    detalles: list[SorteoDetalle] | None = None,
    activos: list[int] | None = None,
    override_palenque: int | None = None,
    override_caballo: str | None = None,
) -> dict:
    palenque_oficial = detalle.palenque
    palenque_tv = palenque_oficial
    if detalles is not None and activos is not None:
        palenque_tv = palenque_tv_automatico(detalle, detalles, activos)
    if override_palenque is not None:
        palenque_tv = override_palenque
    caballo_tv = (override_caballo or "").strip() or detalle.caballo_nombre or "-"
    return {
        "id": detalle.id,
        "orden": detalle.orden,
        "palenque": palenque_tv,
        "palenque_oficial": palenque_oficial,
        "palenque_ajustado": palenque_tv != palenque_oficial,
        "jinete": detalle.jinete_nombre or "-",
        "localidad": detalle.jinete_localidad or "-",
        "caballo": caballo_tv,
        "caballo_oficial": detalle.caballo_nombre or "-",
        "caballo_ajustado": caballo_tv != (detalle.caballo_nombre or "-"),
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


def url_panel_para_sorteo(sorteo: Sorteo | None) -> str:
    if sorteo is None:
        return "/tv"
    return f"/tv?campeonato_id={sorteo.fecha.campeonato_id}&fecha_id={sorteo.fecha_id}&categoria_id={sorteo.categoria_id}"


def sorteo_de_salida(db: Session, salida: TvSalida, tipo: str) -> Sorteo | None:
    attr = {
        "graph": "graph_sorteo_id",
        "ticker": "ticker_sorteo_id",
        "sorteo": "tabla_sorteo_id",
        "campeonato": "campeonato_sorteo_id",
    }[tipo]
    sid = getattr(salida, attr)
    return db.get(Sorteo, sid) if sid else None


def al_aire(salida: TvSalida, tipo: str) -> bool:
    return bool(getattr(salida, {
        "graph": "graph_al_aire",
        "ticker": "ticker_al_aire",
        "sorteo": "tabla_sorteo_al_aire",
        "campeonato": "tabla_campeonato_al_aire",
    }[tipo]))


@router.get("", response_class=HTMLResponse)
def panel_tv(
    request: Request,
    campeonato_id: int | None = Query(default=None),
    fecha_id: int | None = Query(default=None),
    categoria_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    campeonatos, fechas, categorias, sorteo, campeonato_id, fecha_id, categoria_id = contexto_seleccion(
        db, campeonato_id, fecha_id, categoria_id
    )
    detalles = detalles_utiles(sorteo)
    seleccionado = detalle_valido(sorteo, salida.detalle_id)
    if seleccionado is None and detalles:
        seleccionado = detalles[0]

    activos = palenques_activos(salida, categoria_id)
    seleccionado_tv = None
    if seleccionado is not None:
        seleccionado_tv = serializar_detalle(
            seleccionado,
            sorteo.categoria.nombre if sorteo else None,
            detalles=detalles,
            activos=activos,
            override_palenque=salida.graph_override_palenque if salida.graph_sorteo_id == (sorteo.id if sorteo else None) and salida.detalle_id == seleccionado.id else None,
            override_caballo=salida.graph_override_caballo if salida.graph_sorteo_id == (sorteo.id if sorteo else None) and salida.detalle_id == seleccionado.id else None,
        )

    base = str(request.base_url).rstrip("/")
    urls = {tipo: f"{base}/tv/salida/{salida.token}/{tipo}" for tipo in TIPOS_SALIDA}
    previews = {tipo: f"{urls[tipo]}?preview=1" for tipo in TIPOS_SALIDA}

    return templates.TemplateResponse(
        request=request,
        name="tv/panel.html",
        context={
            "menu_activo": "tv",
            "usuario_nombre": request.session.get("usuario_nombre", "TV"),
            "salida": salida,
            "salida_urls": urls,
            "preview_urls": previews,
            "campeonatos": campeonatos,
            "fechas": fechas,
            "categorias": categorias,
            "campeonato_id": campeonato_id,
            "fecha_id": fecha_id,
            "categoria_id": categoria_id,
            "sorteo": sorteo,
            "detalles": detalles,
            "seleccionado": seleccionado,
            "seleccionado_tv": seleccionado_tv,
            "palenques_activos": activos,
        },
    )


@router.post("/graph/preparar")
def preparar_graph(
    request: Request,
    sorteo_id: int = Form(...),
    detalle_id: int = Form(...),
    mostrar_jinete: str | None = Form(default=None),
    mostrar_localidad: str | None = Form(default=None),
    mostrar_caballo: str | None = Form(default=None),
    mostrar_palenque: str | None = Form(default=None),
    mostrar_categoria: str | None = Form(default=None),
    override_palenque: str | None = Form(default=None),
    override_caballo: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    sorteo = db.get(Sorteo, sorteo_id)
    detalle = db.get(SorteoDetalle, detalle_id)
    if sorteo is None or detalle is None or detalle.sorteo_id != sorteo.id or detalle.es_reserva:
        raise HTTPException(status_code=400, detail="Seleccioná un jinete válido del sorteo.")

    # Si se cambia de monta, nunca arrastrar correcciones puntuales de la anterior.
    cambia_monta = salida.detalle_id != detalle.id or salida.graph_sorteo_id != sorteo.id
    salida.graph_sorteo_id = sorteo.id
    salida.sorteo_id = sorteo.id  # compatibilidad
    salida.detalle_id = detalle.id
    salida.graph_mostrar_jinete = mostrar_jinete == "on"
    salida.graph_mostrar_localidad = mostrar_localidad == "on"
    salida.graph_mostrar_caballo = mostrar_caballo == "on"
    salida.graph_mostrar_palenque = mostrar_palenque == "on"
    salida.graph_mostrar_categoria = mostrar_categoria == "on"

    if cambia_monta:
        salida.graph_override_palenque = None
        salida.graph_override_caballo = None
    else:
        valor_palenque = (override_palenque or "").strip()
        salida.graph_override_palenque = int(valor_palenque) if valor_palenque in {"1", "2", "3"} else None
        caballo = (override_caballo or "").strip()
        salida.graph_override_caballo = caballo[:160] if caballo else None

    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = "Graph preparado. La salida al aire no se modificó."
    return RedirectResponse(url_panel_para_sorteo(sorteo), status_code=303)


@router.post("/graph/override")
def guardar_override_graph(
    request: Request,
    sorteo_id: int = Form(...),
    detalle_id: int = Form(...),
    override_palenque: str | None = Form(default=None),
    override_caballo: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    sorteo = db.get(Sorteo, sorteo_id)
    detalle = db.get(SorteoDetalle, detalle_id)
    if sorteo is None or detalle is None or detalle.sorteo_id != sorteo.id or detalle.es_reserva:
        raise HTTPException(status_code=400, detail="Montas TV inválida.")
    salida.graph_sorteo_id = sorteo.id
    salida.sorteo_id = sorteo.id
    salida.detalle_id = detalle.id
    valor_palenque = (override_palenque or "").strip()
    salida.graph_override_palenque = int(valor_palenque) if valor_palenque in {"1", "2", "3"} else None
    caballo = (override_caballo or "").strip()
    salida.graph_override_caballo = caballo[:160] if caballo else None
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = "Corrección puntual de TV actualizada."
    return RedirectResponse(url_panel_para_sorteo(sorteo), status_code=303)


@router.post("/palenques")
def guardar_palenques_tv(
    request: Request,
    sorteo_id: int = Form(...),
    categoria_id: int = Form(...),
    palenque_1: str | None = Form(default=None),
    palenque_2: str | None = Form(default=None),
    palenque_3: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    salida = obtener_o_crear_salida(db)
    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None or sorteo.categoria_id != categoria_id:
        raise HTTPException(status_code=400, detail="Categoría TV inválida.")
    activos = [p for p, valor in ((1, palenque_1), (2, palenque_2), (3, palenque_3)) if valor == "on"]
    if not activos:
        request.session["flash_error"] = "Debe quedar al menos un palenque activo para TV."
        return RedirectResponse(url_panel_para_sorteo(sorteo), status_code=303)
    guardar_palenques_activos(salida, categoria_id, activos)
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = "Palenques operativos de TV guardados para esta categoría."
    return RedirectResponse(url_panel_para_sorteo(sorteo), status_code=303)


@router.post("/salida/{tipo}/preparar")
def preparar_salida(
    request: Request,
    tipo: str,
    sorteo_id: int = Form(...),
    detalle_id: int | None = Form(default=None),
    tabla_pagina: int = Form(default=1),
    tabla_auto: str | None = Form(default=None),
    ticker_cantidad: int = Form(default=6),
    db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    if tipo not in {"ticker", "sorteo", "campeonato"}:
        raise HTTPException(status_code=400, detail="Salida TV inválida.")
    salida = obtener_o_crear_salida(db)
    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado.")

    setattr(salida, {
        "ticker": "ticker_sorteo_id",
        "sorteo": "tabla_sorteo_id",
        "campeonato": "campeonato_sorteo_id",
    }[tipo], sorteo.id)
    if detalle_id:
        detalle = db.get(SorteoDetalle, detalle_id)
        if detalle is not None and detalle.sorteo_id == sorteo.id and not detalle.es_reserva:
            salida.detalle_id = detalle.id
    salida.tabla_pagina = max(1, tabla_pagina)
    salida.tabla_auto = tabla_auto == "on"
    salida.ticker_cantidad = min(20, max(1, ticker_cantidad))
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = f"{tipo.title()} preparado. La salida al aire no se modificó."
    return RedirectResponse(url_panel_para_sorteo(sorteo), status_code=303)


@router.post("/salida/{tipo}/aire")
def cambiar_aire(
    request: Request,
    tipo: str,
    activo: int = Form(...),
    sorteo_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
):
    exigir_operador_tv(request)
    if tipo not in TIPOS_SALIDA:
        raise HTTPException(status_code=400, detail="Salida TV inválida.")
    salida = obtener_o_crear_salida(db)
    attr = {
        "graph": "graph_al_aire",
        "ticker": "ticker_al_aire",
        "sorteo": "tabla_sorteo_al_aire",
        "campeonato": "tabla_campeonato_al_aire",
    }[tipo]
    setattr(salida, attr, bool(activo))
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = f"{tipo.title()} {'al aire' if activo else 'fuera del aire'}."
    sorteo = db.get(Sorteo, sorteo_id) if sorteo_id else None
    return RedirectResponse(url_panel_para_sorteo(sorteo), status_code=303)


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
    # Seguridad operativa: una URL nueva nunca nace al aire.
    salida.graph_al_aire = False
    salida.ticker_al_aire = False
    salida.tabla_sorteo_al_aire = False
    salida.tabla_campeonato_al_aire = False
    salida.actualizado_en = datetime.utcnow()
    db.commit()
    request.session["flash_success"] = "URLs TV regeneradas. Las anteriores quedaron invalidadas y todas las salidas quedaron fuera del aire."
    return RedirectResponse("/tv", status_code=303)


@router.get("/salida/{token}/{tipo}", response_class=HTMLResponse)
def salida_vmix(request: Request, token: str, tipo: str, preview: int = Query(default=0), db: Session = Depends(get_db)):
    if tipo not in TIPOS_SALIDA:
        raise HTTPException(status_code=404, detail="Salida TV no encontrada.")
    salida = db.scalar(select(TvSalida).where(TvSalida.token == token))
    if salida is None:
        raise HTTPException(status_code=404, detail="Salida TV no encontrada.")
    return templates.TemplateResponse(
        request=request,
        name="tv/salida.html",
        context={"token": token, "tipo": tipo, "preview": bool(preview)},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "X-Robots-Tag": "noindex, nofollow, noarchive"},
    )


@router.get("/salida/{token}/{tipo}/estado", response_class=JSONResponse)
def estado_salida_vmix(token: str, tipo: str, preview: int = Query(default=0), db: Session = Depends(get_db)):
    if tipo not in TIPOS_SALIDA:
        raise HTTPException(status_code=404, detail="Salida TV no encontrada.")
    salida = db.scalar(select(TvSalida).where(TvSalida.token == token))
    if salida is None:
        raise HTTPException(status_code=404, detail="Salida TV no encontrada.")

    sorteo = sorteo_de_salida(db, salida, tipo)
    # Durante la preparación, si todavía no se guardó esa salida, usar el sorteo actual legacy para preview.
    if sorteo is None and salida.sorteo_id:
        sorteo = db.get(Sorteo, salida.sorteo_id)
    detalles = detalles_utiles(sorteo)
    actual = detalle_valido(sorteo, salida.detalle_id)
    categoria = sorteo.categoria if sorteo is not None else None
    categoria_nombre = categoria.nombre if categoria else None
    activos = palenques_activos(salida, categoria.id if categoria else None)

    indice_actual = 0
    if actual is not None:
        for i, detalle in enumerate(detalles):
            if detalle.id == actual.id:
                indice_actual = i
                break

    siguientes = detalles[indice_actual + 1: indice_actual + 1 + salida.ticker_cantidad] if actual is not None else detalles[: salida.ticker_cantidad]
    fecha = sorteo.fecha if sorteo is not None else None
    configuracion = {campo: getattr(salida, campo) for campo in DEFAULTS}

    actual_dict = None
    if actual is not None:
        actual_dict = serializar_detalle(
            actual,
            categoria_nombre,
            detalles=detalles,
            activos=activos,
            override_palenque=salida.graph_override_palenque if tipo == "graph" else None,
            override_caballo=salida.graph_override_caballo if tipo == "graph" else None,
        )

    detalles_dict = [serializar_detalle(d, categoria_nombre, detalles=detalles, activos=activos) for d in detalles]
    siguientes_dict = [serializar_detalle(d, categoria_nombre, detalles=detalles, activos=activos) for d in siguientes]

    posiciones = []
    posiciones_disponibles = False
    if tipo == "campeonato" and sorteo is not None and categoria is not None and fecha is not None:
        posiciones = posiciones_campeonato(
            db,
            fecha.campeonato_id,
            categoria.id,
            solo_publicados=False,
        )
        posiciones_disponibles = bool(posiciones)

    visible = bool(preview) or al_aire(salida, tipo)
    return JSONResponse(
        content={
            "tipo": tipo,
            "al_aire": al_aire(salida, tipo),
            "visible": visible,
            "actualizado_en": salida.actualizado_en.isoformat() if salida.actualizado_en else None,
            "campeonato": fecha.campeonato.nombre if fecha else None,
            "fecha": fecha.nombre if fecha else None,
            "fecha_id": fecha.id if fecha else None,
            "categoria": categoria_nombre,
            "actual": actual_dict,
            "detalles": detalles_dict,
            "siguientes": siguientes_dict,
            "tabla_pagina": salida.tabla_pagina,
            "tabla_auto": salida.tabla_auto,
            "filas_por_pagina": salida.tabla_filas,
            "ticker_cantidad": salida.ticker_cantidad,
            "config": configuracion,
            "graph_campos": {
                "jinete": salida.graph_mostrar_jinete,
                "localidad": salida.graph_mostrar_localidad,
                "caballo": salida.graph_mostrar_caballo,
                "palenque": salida.graph_mostrar_palenque,
                "categoria": salida.graph_mostrar_categoria,
            },
            "palenques_activos": activos,
            "posiciones": posiciones,
            "posiciones_disponibles": posiciones_disponibles,
        },
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache", "X-Robots-Tag": "noindex, nofollow, noarchive"},
    )
