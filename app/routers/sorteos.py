from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
from pathlib import Path
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
    # Las pruebas no contaminan la auditoría oficial.
    fecha = db.get(Fecha, fecha_id)
    if fecha is not None:
        campeonato = db.get(Campeonato, fecha.campeonato_id)
        if campeonato is not None and campeonato.modo_prueba:
            return

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
        .order_by(
            CaballoFecha.orden_carga.asc().nullslast(),
            CaballoFecha.id.asc(),
        )
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
    minimo = cantidad_validados + 3
    faltantes = max(0, minimo - cantidad_caballos)
    excedentes_sobre_minimo = max(0, cantidad_caballos - minimo)

    return {
        "categoria": categoria,
        "inscripciones": inscripciones,
        "jinetes_validados": jinetes_validados,
        "caballos": caballos,
        "modo_caballos": (
            "aleatorizar"
            if not asignaciones_caballos
            or asignaciones_caballos[0].aleatorizar_sorteo
            else "mantener_orden"
        ),
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
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            KeepTogether,
            Paragraph,
            SimpleDocTemplate,
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
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title=(
            f"{sorteo.fecha.campeonato.nombre} - "
            f"{sorteo.fecha.nombre} - {sorteo.categoria.nombre}"
        ),
    )

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloSorteo",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=1 * mm,
    )
    subtitulo = ParagraphStyle(
        "SubtituloSorteo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=1 * mm,
    )
    metadata = ParagraphStyle(
        "MetadataSorteo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=11.5,
        alignment=TA_CENTER,
    )
    celda = ParagraphStyle(
        "CeldaSorteo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=11.5,
    )
    celda_centro = ParagraphStyle(
        "CeldaSorteoCentro",
        parent=celda,
        alignment=TA_CENTER,
    )
    cabecera = ParagraphStyle(
        "CabeceraSorteo",
        parent=celda_centro,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=11.5,
    )

    # Recursos institucionales. Se prioriza images/pdf y se mantiene
    # compatibilidad con los recursos existentes directamente en images.
    raiz = Path(__file__).resolve().parents[2]
    logo_path = raiz / "images" / "pdf" / "logo.png"
    bandera_path = raiz / "images" / "pdf" / "bandera.png"
    if not logo_path.exists():
        logo_path = raiz / "images" / "logo.png"
    if not bandera_path.exists():
        bandera_path = raiz / "images" / "bandera.png"

    def imagen_proporcional(path: Path, max_ancho_mm: float, max_alto_mm: float):
        if not path.exists():
            return ""
        imagen = Image(str(path))
        escala = min(
            (max_ancho_mm * mm) / imagen.imageWidth,
            (max_alto_mm * mm) / imagen.imageHeight,
        )
        imagen.drawWidth = imagen.imageWidth * escala
        imagen.drawHeight = imagen.imageHeight * escala
        return imagen

    logo = imagen_proporcional(logo_path, 24, 14)
    bandera = imagen_proporcional(bandera_path, 24, 14)

    fecha_evento = sorteo.fecha.fecha.strftime("%d/%m/%Y")
    fecha_sorteo = fecha_hora_local(sorteo.sorteado_en)
    momento_sorteo = (
        fecha_sorteo.strftime("%d/%m/%Y %H:%M")
        if fecha_sorteo
        else "-"
    )
    usuario_sorteo = sorteo.sorteado_por_nombre or "-"

    encabezado_central = [
        Paragraph(
            "<b>Campeonato Rionegrino de Jineteada</b>",
            titulo,
        ),
        Paragraph(
            "<b>Sergio Herrera</b>",
            ParagraphStyle(
                "SergioHerrera",
                parent=titulo,
                fontSize=14,
                leading=16,
            ),
        ),
        Paragraph(
            (
                f"{sorteo.fecha.campeonato.nombre} - "
                f"{sorteo.fecha.nombre} - {fecha_evento} - "
                f"{sorteo.categoria.nombre.upper()}"
            ),
            subtitulo,
        ),
        Paragraph(
            f"Sorteado: {momento_sorteo} - Por: {usuario_sorteo}",
            metadata,
        ),
    ]

    cabecera_superior = Table(
        [[logo, encabezado_central, bandera]],
        colWidths=[28 * mm, 221 * mm, 28 * mm],
    )
    cabecera_superior.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
        ])
    )

    contenido = [
        KeepTogether([
            cabecera_superior,
            Spacer(1, 2 * mm),
        ])
    ]

    filas = [[
        Paragraph("#", cabecera),
        Paragraph("Palenque", cabecera),
        Paragraph("Jinete", cabecera),
        Paragraph("Localidad", cabecera),
        Paragraph("Caballo", cabecera),
        Paragraph("Tropilla", cabecera),
        Paragraph("Puntos", cabecera),
        Paragraph("Observaciones", cabecera),
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
            Paragraph(f"{detalle.orden:02d}", celda_centro),
            Paragraph(str(detalle.palenque or ""), celda_centro),
            Paragraph(detalle.jinete_nombre or "-", celda),
            Paragraph(detalle.jinete_localidad or "-", celda),
            Paragraph(detalle.caballo_nombre or "-", celda),
            Paragraph(detalle.tropilla_nombre or "-", celda),
            "",
            "",
        ])

    for detalle in detalles_reserva:
        filas.append([
            Paragraph(f"R{detalle.orden}", celda_centro),
            Paragraph("-", celda_centro),
            Paragraph("<b>RESERVA</b>", celda),
            Paragraph("-", celda),
            Paragraph(detalle.caballo_nombre or "-", celda),
            Paragraph(detalle.tropilla_nombre or "-", celda),
            "",
            "",
        ])

    tabla = Table(
        filas,
        repeatRows=1,
        colWidths=[
            10 * mm,
            19 * mm,
            45 * mm,
            43 * mm,
            38 * mm,
            29 * mm,
            20 * mm,
            73 * mm,
        ],
        rowHeights=None,
    )
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#555555")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.3 * mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1.2 * mm),
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

        ids_fechas_validas = {item.id for item in fechas}

        if fecha_id not in ids_fechas_validas:
            fecha_id = fechas[0].id if fechas else 0

        if fecha_id > 0:
            fecha = obtener_fecha_o_404(fecha_id, db)

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
    modo_reserva: str = Form(default="solo_3"),
    modo_caballos: str = Form(default="mantener_actual"),
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

    modo_actual_caballos = datos["modo_caballos"]
    if modo_caballos == "mantener_actual":
        modo_caballos = modo_actual_caballos
    if modo_caballos not in {"aleatorizar", "mantener_orden"}:
        raise HTTPException(status_code=400, detail="Modo de caballos inválido.")

    if not jinetes:
        raise HTTPException(
            status_code=400,
            detail="No hay jinetes validados para sortear.",
        )

    if len(caballos) < len(jinetes) + 3:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Faltan {len(jinetes) + 3 - len(caballos)} "
                "caballo(s). Se requieren los jinetes validados + 3 reservas."
            ),
        )

    # Los jinetes siempre se sortean aleatoriamente.
    jinetes_mezclados = triple_mezcla(jinetes)

    # Los caballos respetan la decisión confirmada antes del sorteo.
    if modo_caballos == "aleatorizar":
        caballos_mezclados = triple_mezcla(caballos)
    else:
        caballos_mezclados = list(caballos)

    # La decisión confirmada pasa a ser la preferencia actual de la tanda.
    asignaciones_modo = db.scalars(
        select(CaballoFecha).where(
            CaballoFecha.fecha_id == fecha.id,
            CaballoFecha.categoria_id == categoria.id,
        )
    ).all()
    for asignacion in asignaciones_modo:
        asignacion.aleatorizar_sorteo = modo_caballos == "aleatorizar"

    if modo_reserva == "todos":
        cantidad_total_caballos = len(caballos_mezclados)
    else:
        cantidad_total_caballos = len(jinetes_mezclados) + 3

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
            f"Jinetes aleatorizados con triple mezcla. "
            f"Caballos: {'aleatorizados con triple mezcla' if modo_caballos == 'aleatorizar' else 'orden de carga/Excel conservado'}. "
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
            "menu_publico": "sorteos",
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
