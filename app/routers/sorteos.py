from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.caballo import Caballo
from app.models.caballo_fecha import CaballoFecha
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.jinete import Jinete
from app.models.jinete_fecha import JineteFecha
from app.models.sorteo import Sorteo, SorteoDetalle
from app.models.sorteo_auditoria import SorteoAuditoria
from app.models.tropilla import Tropilla


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/sorteos",
    tags=["Sorteos"],
)

public_router = APIRouter(
    prefix="/publico/sorteos",
    tags=["Sorteos públicos"],
)


ZONA_HORARIA_LOCAL = ZoneInfo("America/Argentina/Buenos_Aires")


def fecha_hora_local(valor: datetime | None) -> datetime | None:
    """Convierte una fecha guardada en UTC a la hora local de Argentina."""
    if valor is None:
        return None

    # Los DateTime históricos de SQLite son naive pero representan UTC.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)

    return valor.astimezone(ZONA_HORARIA_LOCAL)


def exigir_sesion(request: Request):
    if not request.session.get("usuario_id"):
        return RedirectResponse(
            f"/login?next={request.url.path}",
            status_code=303,
        )
    return None


def exigir_administracion_sorteos(request: Request):
    """Sólo MASTER y ADMIN pueden modificar sorteos."""
    rol = str(request.session.get("usuario_rol") or "").upper()
    if rol not in {"MASTER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="No tiene permisos para modificar sorteos.")


def obtener_fecha_o_404(fecha_id: int, db: Session) -> Fecha:
    fecha = db.get(Fecha, fecha_id)
    if fecha is None:
        raise HTTPException(status_code=404, detail="Fecha no encontrada")
    return fecha


def obtener_categoria_o_404(categoria_id: int, db: Session) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return categoria


def obtener_sorteo(
    fecha_id: int,
    categoria_id: int,
    db: Session,
) -> Sorteo | None:
    return db.scalar(
        select(Sorteo).where(
            Sorteo.fecha_id == fecha_id,
            Sorteo.categoria_id == categoria_id,
        )
    )


def registrar_auditoria(
    request: Request,
    fecha_id: int,
    categoria_id: int,
    evento: str,
    db: Session,
    detalle: str | None = None,
):
    db.add(
        SorteoAuditoria(
            fecha_id=fecha_id,
            categoria_id=categoria_id,
            evento=evento,
            usuario_id=request.session.get("usuario_id"),
            usuario_nombre=request.session.get("usuario_nombre"),
            detalle=detalle,
        )
    )


def triple_mezcla(items: list):
    resultado = list(items)
    generador = secrets.SystemRandom()
    for _ in range(3):
        generador.shuffle(resultado)
    return resultado


def datos_categoria(
    fecha: Fecha,
    categoria: Categoria,
    db: Session,
) -> dict:
    inscripciones = db.scalars(
        select(JineteFecha)
        .where(
            JineteFecha.fecha_id == fecha.id,
            JineteFecha.categoria_id == categoria.id,
        )
        .order_by(JineteFecha.id.asc())
    ).all()

    validados = [
        inscripcion
        for inscripcion in inscripciones
        if inscripcion.estado == "validado"
    ]

    asignaciones_caballos = db.scalars(
        select(CaballoFecha)
        .where(
            CaballoFecha.fecha_id == fecha.id,
            CaballoFecha.categoria_id == categoria.id,
        )
        .order_by(CaballoFecha.id.asc())
    ).all()

    jinetes_validados = []
    for inscripcion in validados:
        jinete = db.get(Jinete, inscripcion.jinete_id)
        if jinete is not None:
            jinetes_validados.append(jinete)

    caballos = []
    for asignacion in asignaciones_caballos:
        caballo = db.get(Caballo, asignacion.caballo_id)
        if caballo is not None:
            caballos.append(caballo)

    cantidad_validados = len(jinetes_validados)
    cantidad_caballos = len(caballos)
    minimo = cantidad_validados + 2
    faltantes = max(0, minimo - cantidad_caballos)
    excedentes_sobre_minimo = max(0, cantidad_caballos - minimo)

    return {
        "categoria": categoria,
        "inscripciones": inscripciones,
        "jinetes_validados": jinetes_validados,
        "caballos": caballos,
        "cantidad_inscriptos": len(inscripciones),
        "cantidad_validados": cantidad_validados,
        "cantidad_caballos": cantidad_caballos,
        "minimo_caballos": minimo,
        "faltantes": faltantes,
        "excedentes_sobre_minimo": excedentes_sobre_minimo,
        "puede_sortear": cantidad_validados > 0 and faltantes == 0,
        "sorteo": obtener_sorteo(fecha.id, categoria.id, db),
    }


def actualizar_bandera_fecha(fecha: Fecha, db: Session):
    cantidad_sorteos = int(
        db.scalar(
            select(func.count(Sorteo.id)).where(
                Sorteo.fecha_id == fecha.id
            )
        )
        or 0
    )
    fecha.sorteada = cantidad_sorteos > 0


def generar_pdf_sorteo(sorteo: Sorteo) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Falta instalar reportlab.",
        ) from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    contenido = [
        Paragraph(
            f"<b>{sorteo.fecha.campeonato.nombre}</b>",
            styles["Title"],
        ),
        Paragraph(
            f"{sorteo.fecha.nombre} - {sorteo.categoria.nombre}",
            styles["Heading2"],
        ),
        Paragraph(
            f"Sorteado: {fecha_hora_local(sorteo.sorteado_en).strftime('%d/%m/%Y %H:%M')} "
            f"- Usuario: {sorteo.sorteado_por_nombre or '-'}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]

    filas = [[
        "Orden",
        "Palenque",
        "Jinete",
        "Localidad",
        "Caballo",
        "Tropilla",
        "Puntos",
        "Observaciones",
    ]]

    detalles_jinetes = [
        detalle
        for detalle in sorteo.detalles
        if not detalle.es_reserva
    ]

    detalles_reserva = [
        detalle
        for detalle in sorteo.detalles
        if detalle.es_reserva
    ]

    for detalle in detalles_jinetes:
        filas.append([
            str(detalle.orden),
            str(detalle.palenque or ""),
            detalle.jinete_nombre or "-",
            detalle.jinete_localidad or "-",
            detalle.caballo_nombre,
            detalle.tropilla_nombre or "-",
            "",
            "",
        ])

    for detalle in detalles_reserva:
        filas.append([
            f"R{detalle.orden}",
            "-",
            "RESERVA",
            "-",
            detalle.caballo_nombre,
            detalle.tropilla_nombre or "-",
            "",
            "",
        ])

    tabla = Table(
        filas,
        repeatRows=1,
        colWidths=[
            16 * mm,
            18 * mm,
            48 * mm,
            34 * mm,
            40 * mm,
            42 * mm,
            25 * mm,
            45 * mm,
        ],
    )
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
        ])
    )
    contenido.append(tabla)

    doc.build(contenido)
    buffer.seek(0)
    return buffer.getvalue()


templates.env.globals["fecha_hora_local"] = fecha_hora_local

@router.get("", response_class=HTMLResponse)
def panel_sorteos(
    request: Request,
    campeonato_id: int = Query(default=0),
    fecha_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    campeonatos = db.scalars(
        select(Campeonato).order_by(Campeonato.id.desc())
    ).all()

    if campeonato_id <= 0 and campeonatos:
        campeonato_id = campeonatos[0].id

    fechas = []
    fecha = None
    secciones = []

    if campeonato_id > 0:
        fechas = db.scalars(
            select(Fecha)
            .where(Fecha.campeonato_id == campeonato_id)
            .order_by(Fecha.fecha.asc())
        ).all()

        if fecha_id <= 0 and fechas:
            fecha_id = fechas[0].id

        if fecha_id > 0:
            fecha = obtener_fecha_o_404(fecha_id, db)
            if fecha.campeonato_id != campeonato_id:
                raise HTTPException(
                    status_code=400,
                    detail="La fecha no pertenece al campeonato seleccionado.",
                )

            categorias = db.scalars(
                select(Categoria)
                .where(
                    Categoria.campeonato_id == campeonato_id,
                    Categoria.activa == True,
                )
                .order_by(Categoria.orden.asc(), Categoria.nombre.asc())
            ).all()

            secciones = [
                datos_categoria(fecha, categoria, db)
                for categoria in categorias
            ]

    return templates.TemplateResponse(
        request=request,
        name="sorteos/panel.html",
        context={
            "campeonatos": campeonatos,
            "campeonato_id": campeonato_id,
            "fechas": fechas,
            "fecha_id": fecha_id,
            "fecha_evento": fecha,
            "secciones": secciones,
            "menu_activo": "sorteos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
            "usuario_rol": str(request.session.get("usuario_rol") or "").upper(),
        },
    )


@router.post("/{fecha_id}/{categoria_id}/realizar")
def realizar_sorteo(
    fecha_id: int,
    categoria_id: int,
    request: Request,
    modo_reserva: str = Form(default="solo_2"),
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    exigir_administracion_sorteos(request)

    fecha = obtener_fecha_o_404(fecha_id, db)
    categoria = obtener_categoria_o_404(categoria_id, db)

    if categoria.campeonato_id != fecha.campeonato_id:
        raise HTTPException(
            status_code=400,
            detail="La categoría no pertenece a la fecha.",
        )

    if obtener_sorteo(fecha_id, categoria_id, db) is not None:
        raise HTTPException(
            status_code=409,
            detail="Esta categoría ya fue sorteada.",
        )

    datos = datos_categoria(fecha, categoria, db)
    jinetes = datos["jinetes_validados"]
    caballos = datos["caballos"]

    if not jinetes:
        raise HTTPException(
            status_code=400,
            detail="No hay jinetes validados para sortear.",
        )

    if len(caballos) < len(jinetes) + 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Faltan {len(jinetes) + 2 - len(caballos)} "
                "caballo(s). Se requieren los jinetes validados + 2 reservas."
            ),
        )

    # Triple mezcla real e independiente.
    jinetes_mezclados = triple_mezcla(jinetes)
    caballos_mezclados = triple_mezcla(caballos)

    if modo_reserva == "todos":
        cantidad_total_caballos = len(caballos_mezclados)
    else:
        cantidad_total_caballos = len(jinetes_mezclados) + 2

    caballos_seleccionados = caballos_mezclados[:cantidad_total_caballos]
    cantidad_reservas = cantidad_total_caballos - len(jinetes_mezclados)

    sorteo = Sorteo(
        fecha_id=fecha.id,
        categoria_id=categoria.id,
        cantidad_caballos_sorteados=cantidad_total_caballos,
        cantidad_reservas=cantidad_reservas,
        sorteado_en=datetime.utcnow(),
        sorteado_por_id=request.session.get("usuario_id"),
        sorteado_por_nombre=request.session.get("usuario_nombre"),
    )
    db.add(sorteo)
    db.flush()

    for indice, jinete in enumerate(jinetes_mezclados, start=1):
        caballo = caballos_seleccionados[indice - 1]
        tropilla = (
            db.get(Tropilla, caballo.tropilla_id)
            if caballo.tropilla_id
            else None
        )

        db.add(
            SorteoDetalle(
                sorteo_id=sorteo.id,
                jinete_id=jinete.id,
                caballo_id=caballo.id,
                orden=indice,
                palenque=((indice - 1) % 3) + 1,
                es_reserva=False,
                jinete_nombre=jinete.nombre_completo,
                jinete_localidad=jinete.localidad,
                caballo_nombre=caballo.nombre,
                tropilla_nombre=(tropilla.nombre if tropilla else None),
            )
        )

    reservas = caballos_seleccionados[len(jinetes_mezclados):]
    for indice, caballo in enumerate(reservas, start=1):
        tropilla = (
            db.get(Tropilla, caballo.tropilla_id)
            if caballo.tropilla_id
            else None
        )
        db.add(
            SorteoDetalle(
                sorteo_id=sorteo.id,
                jinete_id=None,
                caballo_id=caballo.id,
                orden=indice,
                palenque=None,
                es_reserva=True,
                jinete_nombre=None,
                jinete_localidad=None,
                caballo_nombre=caballo.nombre,
                tropilla_nombre=(tropilla.nombre if tropilla else None),
            )
        )

    registrar_auditoria(
        request,
        fecha.id,
        categoria.id,
        "sorteado",
        db,
        detalle=(
            f"Triple mezcla de jinetes y caballos. "
            f"{len(jinetes_mezclados)} jinetes, "
            f"{cantidad_reservas} reservas."
        ),
    )

    db.flush()
    actualizar_bandera_fecha(fecha, db)
    db.commit()

    return RedirectResponse(
        url=f"/sorteos/{sorteo.id}",
        status_code=303,
    )


@router.get("/{sorteo_id}", response_class=HTMLResponse)
def ver_sorteo(
    sorteo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    auditoria = db.scalars(
        select(SorteoAuditoria)
        .where(
            SorteoAuditoria.fecha_id == sorteo.fecha_id,
            SorteoAuditoria.categoria_id == sorteo.categoria_id,
        )
        .order_by(SorteoAuditoria.creado_en.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="sorteos/detalle.html",
        context={
            "sorteo": sorteo,
            "auditoria": auditoria,
            "menu_activo": "sorteos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
            "usuario_rol": str(request.session.get("usuario_rol") or "").upper(),
        },
    )


@router.get("/{sorteo_id}/pdf")
def descargar_pdf_sorteo(
    sorteo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    pdf = generar_pdf_sorteo(sorteo)
    nombre = (
        f"SORTEO_{sorteo.fecha.id}_"
        f"{sorteo.categoria.nombre.replace(' ', '_').upper()}.pdf"
    )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"'
        },
    )


@router.post("/{sorteo_id}/publicar")
def publicar_sorteo(
    sorteo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    exigir_administracion_sorteos(request)

    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    sorteo.publicado = True
    sorteo.publicado_en = datetime.utcnow()

    registrar_auditoria(
        request,
        sorteo.fecha_id,
        sorteo.categoria_id,
        "publicado",
        db,
    )
    db.commit()

    return RedirectResponse(
        url=f"/sorteos/{sorteo.id}",
        status_code=303,
    )


@router.post("/{sorteo_id}/despublicar")
def despublicar_sorteo(
    sorteo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    exigir_administracion_sorteos(request)

    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    sorteo.publicado = False
    sorteo.publicado_en = None

    registrar_auditoria(
        request,
        sorteo.fecha_id,
        sorteo.categoria_id,
        "despublicado",
        db,
    )
    db.commit()

    return RedirectResponse(
        url=f"/sorteos/{sorteo.id}",
        status_code=303,
    )


@router.post("/{sorteo_id}/eliminar")
def eliminar_sorteo(
    sorteo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    redireccion = exigir_sesion(request)
    if redireccion:
        return redireccion

    exigir_administracion_sorteos(request)

    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    fecha = obtener_fecha_o_404(sorteo.fecha_id, db)
    fecha_id = sorteo.fecha_id
    categoria_id = sorteo.categoria_id
    campeonato_id = fecha.campeonato_id

    # Auditoría persistente: queda aunque el sorteo desaparezca.
    registrar_auditoria(
        request,
        fecha_id,
        categoria_id,
        "eliminado_para_resorteo",
        db,
        detalle=(
            f"Se eliminó el sorteo ID {sorteo.id}. "
            "Las inscripciones y caballos permanecen sin cambios."
        ),
    )

    db.delete(sorteo)
    db.flush()
    actualizar_bandera_fecha(fecha, db)
    db.commit()

    return RedirectResponse(
        url=(
            f"/sorteos?campeonato_id={campeonato_id}"
            f"&fecha_id={fecha_id}"
        ),
        status_code=303,
    )


# -------------------------------------------------------------------
# PUBLICO
# -------------------------------------------------------------------

@public_router.get("", response_class=HTMLResponse)
def sorteos_publicos(
    request: Request,
    campeonato_id: int = Query(default=0),
    fecha_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    campeonatos = db.scalars(
        select(Campeonato)
        .join(Fecha, Fecha.campeonato_id == Campeonato.id)
        .join(Sorteo, Sorteo.fecha_id == Fecha.id)
        .where(Sorteo.publicado == True)
        .distinct()
        .order_by(Campeonato.id.desc())
    ).all()

    if campeonato_id <= 0 and campeonatos:
        campeonato_id = campeonatos[0].id

    fechas = []
    sorteos = []

    if campeonato_id > 0:
        fechas = db.scalars(
            select(Fecha)
            .join(Sorteo, Sorteo.fecha_id == Fecha.id)
            .where(
                Fecha.campeonato_id == campeonato_id,
                Sorteo.publicado == True,
            )
            .distinct()
            .order_by(Fecha.fecha.desc())
        ).all()

        if fecha_id <= 0 and fechas:
            fecha_id = fechas[0].id

        if fecha_id > 0:
            sorteos = db.scalars(
                select(Sorteo)
                .join(Categoria, Categoria.id == Sorteo.categoria_id)
                .where(
                    Sorteo.fecha_id == fecha_id,
                    Sorteo.publicado == True,
                )
                .order_by(Categoria.orden.asc(), Categoria.nombre.asc())
            ).all()

    return templates.TemplateResponse(
        request=request,
        name="publico/sorteos.html",
        context={
            "campeonatos": campeonatos,
            "campeonato_id": campeonato_id,
            "fechas": fechas,
            "fecha_id": fecha_id,
            "sorteos": sorteos,
        },
    )


@public_router.get("/{sorteo_id}/pdf")
def pdf_sorteo_publico(
    sorteo_id: int,
    db: Session = Depends(get_db),
):
    sorteo = db.get(Sorteo, sorteo_id)
    if sorteo is None or not sorteo.publicado:
        raise HTTPException(status_code=404, detail="Sorteo no encontrado")

    pdf = generar_pdf_sorteo(sorteo)
    nombre = (
        f"SORTEO_{sorteo.fecha.id}_"
        f"{sorteo.categoria.nombre.replace(' ', '_').upper()}.pdf"
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"'
        },
    )
