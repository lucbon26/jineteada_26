from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
import secrets
import unicodedata
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.jinete import Jinete
from app.models.jinete_campeonato import JineteCampeonato
from app.models.jinete_fecha import JineteFecha


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/inscripciones",
    tags=["Inscripciones"],
)


ESTADOS_INSCRIPCION = {
    "pendiente",
    "validado",
    "ausente",
    "no_habilitado",
}


def obtener_fecha_o_404(fecha_id: int, db: Session) -> Fecha:
    fecha = db.get(Fecha, fecha_id)
    if fecha is None:
        raise HTTPException(status_code=404, detail="Fecha no encontrada")
    return fecha


def obtener_inscripcion(
    jinete_id: int,
    fecha_id: int,
    db: Session,
) -> JineteFecha | None:
    return db.scalar(
        select(JineteFecha).where(
            JineteFecha.jinete_id == jinete_id,
            JineteFecha.fecha_id == fecha_id,
        )
    )


def cantidad_ausencias_campeonato(
    jinete_id: int,
    campeonato_id: int,
    db: Session,
) -> int:
    return int(
        db.scalar(
            select(func.count(JineteFecha.id))
            .join(Fecha, Fecha.id == JineteFecha.fecha_id)
            .where(
                JineteFecha.jinete_id == jinete_id,
                Fecha.campeonato_id == campeonato_id,
                JineteFecha.estado == "ausente",
            )
        )
        or 0
    )


def cantidad_suspensiones_campeonato(
    jinete_id: int,
    campeonato_id: int,
    db: Session,
) -> int:
    return int(
        db.scalar(
            select(func.count(JineteFecha.id))
            .join(Fecha, Fecha.id == JineteFecha.fecha_id)
            .where(
                JineteFecha.jinete_id == jinete_id,
                Fecha.campeonato_id == campeonato_id,
                JineteFecha.estado == "no_habilitado",
                JineteFecha.motivo_no_habilitado == "suspendido",
            )
        )
        or 0
    )


def asegurar_qr_token(jinete: Jinete, db: Session) -> str:
    if jinete.qr_token:
        return jinete.qr_token

    while True:
        token = secrets.token_urlsafe(24)
        existe = db.scalar(
            select(Jinete.id).where(Jinete.qr_token == token)
        )
        if not existe:
            jinete.qr_token = token
            db.flush()
            return token


def preparar_inscripciones_fecha(
    fecha: Fecha,
    db: Session,
) -> int:
    """Crea las inscripciones que faltan para una fecha abierta.

    Los jinetes activos quedan pendientes de QR. Los suspendidos figuran
    como no habilitados. Inactivos y descalificados no se autoinscriben.
    Es idempotente: nunca duplica Jinete + Fecha.
    """
    if fecha.inscripcion_cerrada:
        return 0

    preinscriptos = db.scalars(
        select(JineteCampeonato)
        .where(
            JineteCampeonato.campeonato_id == fecha.campeonato_id,
            JineteCampeonato.categoria_id.is_not(None),
        )
        .order_by(JineteCampeonato.id.asc())
    ).all()

    creadas = 0

    for pre in preinscriptos:
        jinete = db.get(Jinete, pre.jinete_id)
        if jinete is None:
            continue

        if obtener_inscripcion(jinete.id, fecha.id, db) is not None:
            continue

        if jinete.estado in {"inactivo", "descalificado"}:
            continue

        estado = "pendiente"
        motivo = None

        if jinete.estado == "suspendido":
            estado = "no_habilitado"
            motivo = "suspendido"

        db.add(
            JineteFecha(
                jinete_id=jinete.id,
                fecha_id=fecha.id,
                categoria_id=pre.categoria_id,
                estado=estado,
                motivo_no_habilitado=motivo,
            )
        )
        creadas += 1

    if creadas:
        db.commit()

    return creadas


def generar_qr_png_bytes(texto: str) -> bytes | None:
    try:
        import qrcode
    except ImportError:
        return None

    imagen = qrcode.make(texto)
    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def normalizar_nombre_archivo(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor or "")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.upper().strip()
    texto = "".join(
        caracter if caracter.isalnum() else "_"
        for caracter in texto
    )
    while "__" in texto:
        texto = texto.replace("__", "_")
    return texto.strip("_") or "SIN_DATO"


def obtener_asignacion_qr(
    jinete_id: int,
    db: Session,
    campeonato_id: int = 0,
) -> JineteCampeonato | None:
    consulta = (
        select(JineteCampeonato)
        .where(
            JineteCampeonato.jinete_id == jinete_id,
            JineteCampeonato.categoria_id.is_not(None),
        )
        .order_by(JineteCampeonato.id.desc())
    )

    if campeonato_id > 0:
        consulta = consulta.where(
            JineteCampeonato.campeonato_id == campeonato_id
        )

    return db.scalar(consulta)


def nombre_pdf_jinete(
    jinete: Jinete,
    categoria: Categoria,
) -> str:
    nombres = normalizar_nombre_archivo(jinete.nombres)
    apellidos = normalizar_nombre_archivo(jinete.apellidos)
    categoria_nombre = normalizar_nombre_archivo(categoria.nombre)
    return f"{nombres}_{apellidos}_{categoria_nombre}.pdf"


def generar_pdf_qr_bytes(
    jinete: Jinete,
    categoria: Categoria,
    campeonato: Campeonato | None,
    db: Session,
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A6
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Falta instalar la dependencia reportlab.",
        ) from exc

    token = asegurar_qr_token(jinete, db)
    png = generar_qr_png_bytes(f"JINETE:{token}")

    if png is None:
        raise HTTPException(
            status_code=500,
            detail="Falta instalar la dependencia qrcode[pil].",
        )

    buffer = BytesIO()
    ancho, alto = A6
    pdf = canvas.Canvas(buffer, pagesize=A6)

    campeonato_nombre = (
        getattr(campeonato, "nombre", None)
        or "Campeonato"
    )

    pdf.setTitle(
        f"{jinete.nombres} {jinete.apellidos} - {categoria.nombre}"
    )

    # Encabezado
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(
        ancho / 2,
        alto - 28,
        campeonato_nombre[:44],
    )

    # Nombre
    nombre = f"{jinete.nombres} {jinete.apellidos}".upper()
    pdf.setFont("Helvetica-Bold", 15)

    if len(nombre) <= 30:
        pdf.drawCentredString(ancho / 2, alto - 56, nombre)
        y_datos = alto - 78
    else:
        palabras = nombre.split()
        corte = max(1, len(palabras) // 2)
        linea_1 = " ".join(palabras[:corte])
        linea_2 = " ".join(palabras[corte:])
        pdf.drawCentredString(ancho / 2, alto - 53, linea_1[:36])
        pdf.drawCentredString(ancho / 2, alto - 70, linea_2[:36])
        y_datos = alto - 91

    # DNI y categoría
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(ancho / 2, y_datos, f"DNI {jinete.dni}")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(
        ancho / 2,
        y_datos - 18,
        categoria.nombre.upper()[:36],
    )

    # QR grande
    qr_tamano = 180
    qr_x = (ancho - qr_tamano) / 2
    qr_y = 42

    pdf.drawImage(
        ImageReader(BytesIO(png)),
        qr_x,
        qr_y,
        width=qr_tamano,
        height=qr_tamano,
        preserveAspectRatio=True,
        mask="auto",
    )

    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(
        ancho / 2,
        27,
        "QR unico y permanente del jinete",
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()


@router.get("", response_class=HTMLResponse)
def panel_inscripciones(
    request: Request,
    campeonato_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    campeonatos = db.scalars(
        select(Campeonato).order_by(Campeonato.id.desc())
    ).all()

    fechas = []
    if campeonato_id > 0:
        campeonato = db.get(Campeonato, campeonato_id)
        if campeonato is None:
            raise HTTPException(status_code=404, detail="Campeonato no encontrado.")

        fechas = db.scalars(
            select(Fecha)
            .where(Fecha.campeonato_id == campeonato_id)
            .order_by(Fecha.fecha.asc())
        ).all()

    resumen_fechas: dict[int, dict[str, int]] = {}
    for fecha in fechas:
        filas = db.scalars(
            select(JineteFecha).where(JineteFecha.fecha_id == fecha.id)
        ).all()
        resumen_fechas[fecha.id] = {
            "total": len(filas),
            "pendiente": sum(1 for x in filas if x.estado == "pendiente"),
            "validado": sum(1 for x in filas if x.estado == "validado"),
            "ausente": sum(1 for x in filas if x.estado == "ausente"),
            "no_habilitado": sum(
                1 for x in filas if x.estado == "no_habilitado"
            ),
        }

    return templates.TemplateResponse(
        request=request,
        name="inscripciones/panel.html",
        context={
            "campeonatos": campeonatos,
            "fechas": fechas,
            "campeonato_id": campeonato_id,
            "resumen_fechas": resumen_fechas,
            "menu_activo": "inscripciones",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/generar")
def generar_inscripciones_varias_fechas(
    request: Request,
    campeonato_id: int = Form(...),
    fecha_ids: list[int] | None = Form(None),
    db: Session = Depends(get_db),
):
    if not fecha_ids:
        raise HTTPException(
            status_code=400,
            detail="Seleccioná al menos una fecha para generar las inscripciones.",
        )

    campeonato = db.get(Campeonato, campeonato_id)
    if campeonato is None:
        raise HTTPException(status_code=404, detail="Campeonato no encontrado.")

    creadas = 0
    procesadas = 0

    for fecha_id in fecha_ids:
        fecha = db.get(Fecha, fecha_id)
        if fecha is None:
            continue
        if fecha.campeonato_id != campeonato_id:
            raise HTTPException(
                status_code=400,
                detail="Una de las fechas seleccionadas no pertenece al campeonato activo.",
            )
        if fecha.inscripcion_cerrada:
            continue
        creadas += preparar_inscripciones_fecha(fecha, db)
        procesadas += 1

    return RedirectResponse(
        url=(
            f"/inscripciones?campeonato_id={campeonato_id}"
            f"&generadas={creadas}&fechas={procesadas}"
        ),
        status_code=303,
    )


@router.get("/fecha/{fecha_id}", response_class=HTMLResponse)
def detalle_inscripciones_fecha(
    fecha_id: int,
    request: Request,
    buscar: str = Query(default=""),
    categoria_id: int = Query(default=0),
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db),
):
    fecha = obtener_fecha_o_404(fecha_id, db)

    # La autoinscripción ocurre al entrar a una fecha abierta. Es idempotente.
    preparar_inscripciones_fecha(fecha, db)

    consulta = (
        select(JineteFecha)
        .join(Jinete, Jinete.id == JineteFecha.jinete_id)
        .where(JineteFecha.fecha_id == fecha.id)
    )

    texto = buscar.strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.where(
            or_(
                Jinete.nombres.ilike(patron),
                Jinete.apellidos.ilike(patron),
                Jinete.dni.ilike(patron),
                Jinete.localidad.ilike(patron),
            )
        )

    if categoria_id > 0:
        consulta = consulta.where(JineteFecha.categoria_id == categoria_id)

    if estado in ESTADOS_INSCRIPCION:
        consulta = consulta.where(JineteFecha.estado == estado)

    inscripciones = db.scalars(
        consulta.order_by(Jinete.apellidos.asc(), Jinete.nombres.asc())
    ).all()

    todas = db.scalars(
        select(JineteFecha).where(JineteFecha.fecha_id == fecha.id)
    ).all()

    categorias = db.scalars(
        select(Categoria)
        .where(Categoria.campeonato_id == fecha.campeonato_id)
        .order_by(Categoria.orden.asc(), Categoria.nombre.asc())
    ).all()

    resumen = {
        "total": len(todas),
        "pendiente": sum(1 for x in todas if x.estado == "pendiente"),
        "validado": sum(1 for x in todas if x.estado == "validado"),
        "ausente": sum(1 for x in todas if x.estado == "ausente"),
        "no_habilitado": sum(1 for x in todas if x.estado == "no_habilitado"),
    }

    return templates.TemplateResponse(
        request=request,
        name="inscripciones/fecha.html",
        context={
            "fecha_evento": fecha,
            "inscripciones": inscripciones,
            "categorias": categorias,
            "buscar": buscar,
            "categoria_id": categoria_id,
            "estado_filtro": estado,
            "resumen": resumen,
            "mensaje": request.query_params.get("mensaje"),
            "tipo": request.query_params.get("tipo", "info"),
            "menu_activo": "inscripciones",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/fecha/{fecha_id}/validar-qr")
def validar_qr(
    fecha_id: int,
    request: Request,
    codigo: str = Form(...),
    db: Session = Depends(get_db),
):
    fecha = obtener_fecha_o_404(fecha_id, db)

    if fecha.inscripcion_cerrada:
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=danger&mensaje=La inscripción está cerrada."
            ),
            status_code=303,
        )

    codigo = codigo.strip()
    if codigo.upper().startswith("JINETE:"):
        codigo = codigo.split(":", 1)[1].strip()

    jinete = db.scalar(
        select(Jinete).where(Jinete.qr_token == codigo)
    )

    if jinete is None:
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=danger&mensaje=QR no reconocido."
            ),
            status_code=303,
        )

    inscripcion = obtener_inscripcion(jinete.id, fecha.id, db)
    if inscripcion is None:
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=warning&mensaje="
                f"{jinete.apellidos}, {jinete.nombres} no está inscripto en esta fecha."
            ),
            status_code=303,
        )

    if inscripcion.estado == "validado":
        hora = (
            inscripcion.validado_en.strftime("%H:%M")
            if inscripcion.validado_en
            else ""
        )
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=warning&mensaje="
                f"{jinete.apellidos}, {jinete.nombres} ya estaba validado {hora}."
            ),
            status_code=303,
        )

    if jinete.estado != "activo":
        inscripcion.estado = "no_habilitado"
        inscripcion.motivo_no_habilitado = jinete.estado
        db.commit()
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=danger&mensaje="
                f"{jinete.apellidos}, {jinete.nombres} no está habilitado: {jinete.estado}."
            ),
            status_code=303,
        )

    if inscripcion.estado != "pendiente":
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=warning&mensaje="
                f"La inscripción de {jinete.apellidos}, {jinete.nombres} "
                f"está en estado {inscripcion.estado}."
            ),
            status_code=303,
        )

    inscripcion.estado = "validado"
    inscripcion.validado_en = datetime.utcnow()
    inscripcion.validado_por = request.session.get(
        "usuario_nombre",
        "Administrador",
    )
    inscripcion.motivo_no_habilitado = None
    db.commit()

    return RedirectResponse(
        url=(
            f"/inscripciones/fecha/{fecha_id}"
            "?tipo=success&mensaje="
            f"QR validado: {jinete.apellidos}, {jinete.nombres}. Habilitado para sorteo."
        ),
        status_code=303,
    )


@router.post("/fecha/{fecha_id}/cerrar")
def cerrar_inscripcion(
    fecha_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    fecha = obtener_fecha_o_404(fecha_id, db)

    if fecha.inscripcion_cerrada:
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=warning&mensaje=La inscripción ya estaba cerrada."
            ),
            status_code=303,
        )

    inscripciones = db.scalars(
        select(JineteFecha).where(JineteFecha.fecha_id == fecha.id)
    ).all()

    ausentes = 0
    descalificados_faltas = 0
    descalificados_suspension = 0

    for inscripcion in inscripciones:
        jinete = db.get(Jinete, inscripcion.jinete_id)
        if jinete is None:
            continue

        # Al cierre se respeta el estado maestro actual del jinete.
        if inscripcion.estado == "pendiente":
            if jinete.estado == "inactivo":
                inscripcion.estado = "no_habilitado"
                inscripcion.motivo_no_habilitado = "inactivo"
            elif jinete.estado == "descalificado":
                inscripcion.estado = "no_habilitado"
                inscripcion.motivo_no_habilitado = "descalificado"
            elif jinete.estado == "suspendido":
                inscripcion.estado = "no_habilitado"
                inscripcion.motivo_no_habilitado = "suspendido"
            else:
                inscripcion.estado = "ausente"
                inscripcion.motivo_no_habilitado = None
                ausentes += 1

        db.flush()

        if inscripcion.estado == "ausente" and jinete.estado != "inactivo":
            faltas = cantidad_ausencias_campeonato(
                jinete.id,
                fecha.campeonato_id,
                db,
            )
            if faltas >= 2 and jinete.estado != "descalificado":
                jinete.estado = "descalificado"
                descalificados_faltas += 1

        if (
            inscripcion.estado == "no_habilitado"
            and inscripcion.motivo_no_habilitado == "suspendido"
            and jinete.estado != "inactivo"
        ):
            suspensiones = cantidad_suspensiones_campeonato(
                jinete.id,
                fecha.campeonato_id,
                db,
            )
            if suspensiones >= 2 and jinete.estado != "descalificado":
                jinete.estado = "descalificado"
                descalificados_suspension += 1

    fecha.inscripcion_cerrada = True
    fecha.inscripcion_cerrada_en = datetime.utcnow()
    db.commit()

    mensaje = (
        f"Inscripción cerrada. {ausentes} ausente(s). "
        f"{descalificados_faltas} descalificado(s) por 2 faltas. "
        f"{descalificados_suspension} descalificado(s) por límite de suspensión."
    )

    return RedirectResponse(
        url=(
            f"/inscripciones/fecha/{fecha_id}"
            f"?tipo=success&mensaje={mensaje}"
        ),
        status_code=303,
    )


@router.post("/fecha/{fecha_id}/reabrir")
def reabrir_inscripcion(
    fecha_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    fecha = obtener_fecha_o_404(fecha_id, db)

    if fecha.sorteada:
        return RedirectResponse(
            url=(
                f"/inscripciones/fecha/{fecha_id}"
                "?tipo=danger&mensaje=No se puede reabrir: la fecha ya fue sorteada."
            ),
            status_code=303,
        )

    fecha.inscripcion_cerrada = False
    fecha.inscripcion_cerrada_en = None
    db.commit()

    return RedirectResponse(
        url=(
            f"/inscripciones/fecha/{fecha_id}"
            "?tipo=warning&mensaje=Inscripción reabierta. Las sanciones ya aplicadas no se revierten automáticamente."
        ),
        status_code=303,
    )


@router.get("/qr", response_class=HTMLResponse)
def listado_qr_jinetes(
    request: Request,
    buscar: str = Query(default=""),
    campeonato_id: int = Query(default=0),
    categoria_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    campeonatos = db.scalars(
        select(Campeonato).order_by(Campeonato.id.desc())
    ).all()

    categorias = []
    filas_qr = []

    if campeonato_id > 0:
        categorias = db.scalars(
            select(Categoria)
            .where(Categoria.campeonato_id == campeonato_id)
            .order_by(Categoria.orden.asc(), Categoria.nombre.asc())
        ).all()

        consulta = (
            select(JineteCampeonato)
            .join(Jinete, Jinete.id == JineteCampeonato.jinete_id)
            .where(
                JineteCampeonato.campeonato_id == campeonato_id,
                JineteCampeonato.categoria_id.is_not(None),
            )
        )

        if categoria_id > 0:
            consulta = consulta.where(
                JineteCampeonato.categoria_id == categoria_id
            )

        texto = buscar.strip()
        if texto:
            patron = f"%{texto}%"
            consulta = consulta.where(
                or_(
                    Jinete.nombres.ilike(patron),
                    Jinete.apellidos.ilike(patron),
                    Jinete.dni.ilike(patron),
                )
            )

        asignaciones = db.scalars(
            consulta.order_by(
                Jinete.apellidos.asc(),
                Jinete.nombres.asc(),
            )
        ).all()

        for asignacion in asignaciones:
            jinete = db.get(Jinete, asignacion.jinete_id)
            categoria = db.get(Categoria, asignacion.categoria_id)

            if jinete is None or categoria is None:
                continue

            asegurar_qr_token(jinete, db)
            filas_qr.append({
                "jinete": jinete,
                "categoria": categoria,
            })

        db.commit()

    return templates.TemplateResponse(
        request=request,
        name="inscripciones/qr_listado.html",
        context={
            "filas_qr": filas_qr,
            "buscar": buscar,
            "campeonatos": campeonatos,
            "campeonato_id": campeonato_id,
            "categorias": categorias,
            "categoria_id": categoria_id,
            "menu_activo": "inscripciones",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


# IMPORTANTE: esta ruta está antes de /qr/{jinete_id} para evitar
# que FastAPI interprete "zip" como un ID de jinete.
@router.get("/qr/zip")
def descargar_qr_bulk_zip(
    campeonato_id: int = Query(..., gt=0),
    categoria_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    campeonato = db.get(Campeonato, campeonato_id)

    if campeonato is None:
        raise HTTPException(
            status_code=404,
            detail="Campeonato no encontrado",
        )

    consulta = (
        select(JineteCampeonato)
        .join(Jinete, Jinete.id == JineteCampeonato.jinete_id)
        .where(
            JineteCampeonato.campeonato_id == campeonato_id,
            JineteCampeonato.categoria_id.is_not(None),
        )
    )

    categoria_filtro = None

    if categoria_id > 0:
        categoria_filtro = db.get(Categoria, categoria_id)

        if (
            categoria_filtro is None
            or categoria_filtro.campeonato_id != campeonato_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Categoría no encontrada en este campeonato",
            )

        consulta = consulta.where(
            JineteCampeonato.categoria_id == categoria_id
        )

    asignaciones = db.scalars(
        consulta.order_by(
            Jinete.apellidos.asc(),
            Jinete.nombres.asc(),
        )
    ).all()

    if not asignaciones:
        raise HTTPException(
            status_code=404,
            detail="No hay jinetes para generar.",
        )

    zip_buffer = BytesIO()
    nombres_usados: set[str] = set()

    with ZipFile(
        zip_buffer,
        "w",
        compression=ZIP_DEFLATED,
    ) as archivo_zip:
        for asignacion in asignaciones:
            jinete = db.get(Jinete, asignacion.jinete_id)
            categoria = db.get(Categoria, asignacion.categoria_id)

            if jinete is None or categoria is None:
                continue

            pdf = generar_pdf_qr_bytes(
                jinete,
                categoria,
                campeonato,
                db,
            )

            nombre = nombre_pdf_jinete(
                jinete,
                categoria,
            )

            # Evita que dos homónimos se pisen dentro del ZIP.
            if nombre in nombres_usados:
                base_nombre = nombre[:-4]
                dni = normalizar_nombre_archivo(jinete.dni)
                nombre = f"{base_nombre}_{dni}.pdf"

            nombres_usados.add(nombre)
            archivo_zip.writestr(nombre, pdf)

    db.commit()
    zip_buffer.seek(0)

    if categoria_filtro is not None:
        etiqueta = normalizar_nombre_archivo(
            categoria_filtro.nombre
        )
        nombre_zip = f"QR_{etiqueta}.zip"
    else:
        nombre_zip = "QR_TODOS.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition":
                f'attachment; filename="{nombre_zip}"'
        },
    )


@router.get("/qr/{jinete_id}", response_class=HTMLResponse)
def ver_qr_jinete(
    jinete_id: int,
    request: Request,
    campeonato_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    jinete = db.get(Jinete, jinete_id)

    if jinete is None:
        raise HTTPException(
            status_code=404,
            detail="Jinete no encontrado",
        )

    asignacion = obtener_asignacion_qr(
        jinete.id,
        db,
        campeonato_id=campeonato_id,
    )

    categoria = (
        db.get(Categoria, asignacion.categoria_id)
        if asignacion and asignacion.categoria_id
        else None
    )

    campeonato = (
        db.get(Campeonato, asignacion.campeonato_id)
        if asignacion
        else None
    )

    token = asegurar_qr_token(jinete, db)
    db.commit()

    payload = f"JINETE:{token}"
    png = generar_qr_png_bytes(payload)
    qr_base64 = (
        base64.b64encode(png).decode("ascii")
        if png
        else None
    )

    return templates.TemplateResponse(
        request=request,
        name="inscripciones/qr_jinete.html",
        context={
            "jinete": jinete,
            "payload": payload,
            "qr_base64": qr_base64,
            "categoria": categoria,
            "campeonato": campeonato,
            "campeonato_id": (
                asignacion.campeonato_id
                if asignacion
                else 0
            ),
            "menu_activo": "inscripciones",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.get("/qr/{jinete_id}/pdf")
def descargar_qr_jinete_pdf(
    jinete_id: int,
    campeonato_id: int = Query(default=0),
    db: Session = Depends(get_db),
):
    jinete = db.get(Jinete, jinete_id)

    if jinete is None:
        raise HTTPException(
            status_code=404,
            detail="Jinete no encontrado",
        )

    asignacion = obtener_asignacion_qr(
        jinete.id,
        db,
        campeonato_id=campeonato_id,
    )

    if asignacion is None or asignacion.categoria_id is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "El jinete no tiene categoría asignada "
                "en el campeonato."
            ),
        )

    categoria = db.get(
        Categoria,
        asignacion.categoria_id,
    )
    campeonato = db.get(
        Campeonato,
        asignacion.campeonato_id,
    )

    if categoria is None:
        raise HTTPException(
            status_code=404,
            detail="Categoría no encontrada.",
        )

    pdf = generar_pdf_qr_bytes(
        jinete,
        categoria,
        campeonato,
        db,
    )

    db.commit()

    nombre = nombre_pdf_jinete(
        jinete,
        categoria,
    )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{nombre}"'
        },
    )


@router.get("/qr/{jinete_id}/png")
def descargar_qr_jinete(
    jinete_id: int,
    db: Session = Depends(get_db),
):
    jinete = db.get(Jinete, jinete_id)
    if jinete is None:
        raise HTTPException(status_code=404, detail="Jinete no encontrado")

    token = asegurar_qr_token(jinete, db)
    db.commit()

    png = generar_qr_png_bytes(f"JINETE:{token}")
    if png is None:
        raise HTTPException(
            status_code=500,
            detail="Falta instalar la dependencia qrcode[pil].",
        )

    nombre = f"qr_{jinete.apellidos}_{jinete.nombres}_{jinete.dni}.png"
    nombre = "_".join(nombre.split())

    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"'
        },
    )


@router.post("/qr/{jinete_id}/regenerar")
def regenerar_qr_jinete(
    jinete_id: int,
    db: Session = Depends(get_db),
):
    jinete = db.get(Jinete, jinete_id)
    if jinete is None:
        raise HTTPException(status_code=404, detail="Jinete no encontrado")

    while True:
        token = secrets.token_urlsafe(24)
        existe = db.scalar(
            select(Jinete.id).where(
                Jinete.qr_token == token,
                Jinete.id != jinete.id,
            )
        )
        if not existe:
            break

    jinete.qr_token = token
    db.commit()

    return RedirectResponse(
        url=f"/inscripciones/qr/{jinete_id}",
        status_code=303,
    )
