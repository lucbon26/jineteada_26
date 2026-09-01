from __future__ import annotations

import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.jinete import Jinete
from app.models.jinete_fecha import JineteFecha
from app.routers.inscripciones import obtener_inscripcion, preparar_inscripciones_fecha

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/acreditacion", tags=["Acreditación"])


def normalizar_rol(valor: str | None) -> str:
    texto = (valor or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def usuario_puede_acreditar(request: Request) -> bool:
    return normalizar_rol(request.session.get("usuario_rol")) in {
        "admin",
        "administrador",
        "secretaria",
        "acreditacion",
    }


def exigir_acceso(request: Request):
    if not request.session.get("usuario_id"):
        return RedirectResponse(url="/login?next=/acreditacion", status_code=303)
    if not usuario_puede_acreditar(request):
        return RedirectResponse(url="/", status_code=303)
    return None


def respuesta_error(http: int, titulo: str, mensaje: str, codigo: str):
    return JSONResponse(
        status_code=http,
        content={
            "ok": False,
            "codigo": codigo,
            "titulo": titulo,
            "mensaje": mensaje,
        },
    )


@router.get("", response_class=HTMLResponse)
def pantalla_acreditacion(
    request: Request,
    fecha_id: int = 0,
    db: Session = Depends(get_db),
):
    bloqueo = exigir_acceso(request)
    if bloqueo:
        return bloqueo

    fechas = db.scalars(
        select(Fecha).order_by(Fecha.fecha.asc(), Fecha.id.asc())
    ).all()

    fecha_seleccionada = None
    resumen = {
        "total": 0,
        "pendiente": 0,
        "validado": 0,
        "ausente": 0,
        "no_habilitado": 0,
    }

    if fecha_id:
        fecha_seleccionada = db.get(Fecha, fecha_id)
        if fecha_seleccionada is not None:
            if not fecha_seleccionada.inscripcion_cerrada:
                preparar_inscripciones_fecha(fecha_seleccionada, db)

            inscripciones = db.scalars(
                select(JineteFecha).where(
                    JineteFecha.fecha_id == fecha_seleccionada.id
                )
            ).all()

            resumen = {
                "total": len(inscripciones),
                "pendiente": sum(x.estado == "pendiente" for x in inscripciones),
                "validado": sum(x.estado == "validado" for x in inscripciones),
                "ausente": sum(x.estado == "ausente" for x in inscripciones),
                "no_habilitado": sum(
                    x.estado == "no_habilitado" for x in inscripciones
                ),
            }
            request.session["acreditacion_fecha_id"] = fecha_seleccionada.id

    elif request.session.get("acreditacion_fecha_id"):
        guardada = int(request.session["acreditacion_fecha_id"])
        if db.get(Fecha, guardada):
            return RedirectResponse(
                url=f"/acreditacion?fecha_id={guardada}",
                status_code=303,
            )

    return templates.TemplateResponse(
        request=request,
        name="acreditacion/mobile.html",
        context={
            "fechas": fechas,
            "fecha_evento": fecha_seleccionada,
            "resumen": resumen,
            "usuario_nombre": request.session.get(
                "usuario_nombre", "Acreditación"
            ),
            "usuario_rol": request.session.get("usuario_rol", ""),
        },
    )


@router.post("/validar")
def validar_desde_celular(
    request: Request,
    fecha_id: int = Form(...),
    codigo: str = Form(...),
    db: Session = Depends(get_db),
):
    if not request.session.get("usuario_id") or not usuario_puede_acreditar(request):
        return respuesta_error(
            401, "SESIÓN VENCIDA", "Volvé a iniciar sesión.", "sesion"
        )

    fecha = db.get(Fecha, fecha_id)
    if fecha is None:
        return respuesta_error(
            404, "FECHA NO ENCONTRADA", "La fecha seleccionada no existe.", "fecha"
        )

    if fecha.inscripcion_cerrada:
        return respuesta_error(
            409,
            "INSCRIPCIÓN CERRADA",
            "No se admiten más acreditaciones para esta fecha.",
            "cerrada",
        )

    preparar_inscripciones_fecha(fecha, db)

    valor = codigo.strip()
    if valor.upper().startswith("JINETE:"):
        valor = valor.split(":", 1)[1].strip()

    jinete = db.scalar(select(Jinete).where(Jinete.qr_token == valor))
    if jinete is None:
        return respuesta_error(
            404,
            "QR NO RECONOCIDO",
            "El código leído no corresponde a ningún jinete.",
            "qr_invalido",
        )

    nombre = f"{jinete.apellidos}, {jinete.nombres}"

    if jinete.estado == "inactivo":
        return respuesta_error(
            409, "INACTIVO", f"{nombre} está inactivo.", "inactivo"
        )
    if jinete.estado == "suspendido":
        return respuesta_error(
            409,
            "SUSPENDIDO",
            f"{nombre} está suspendido para esta fecha.",
            "suspendido",
        )
    if jinete.estado == "descalificado":
        return respuesta_error(
            409,
            "DESCALIFICADO",
            f"{nombre} no está habilitado para participar.",
            "descalificado",
        )

    inscripcion = obtener_inscripcion(jinete.id, fecha.id, db)
    if inscripcion is None:
        return respuesta_error(
            404,
            "NO INSCRIPTO",
            f"{nombre} no está inscripto en esta fecha.",
            "no_inscripto",
        )

    categoria = db.get(Categoria, inscripcion.categoria_id)
    categoria_nombre = categoria.nombre if categoria else ""

    if inscripcion.estado == "validado":
        hora = (
            inscripcion.validado_en.strftime("%H:%M")
            if inscripcion.validado_en else ""
        )
        return JSONResponse(
            content={
                "ok": False,
                "codigo": "ya_validado",
                "titulo": "YA VALIDADO",
                "mensaje": (
                    f"{nombre} ya había sido acreditado"
                    + (f" a las {hora}." if hora else ".")
                ),
                "jinete": nombre,
                "categoria": categoria_nombre,
                "hora": hora,
            }
        )

    if inscripcion.estado != "pendiente":
        etiqueta = {
            "ausente": "AUSENTE",
            "no_habilitado": "NO HABILITADO",
        }.get(inscripcion.estado, inscripcion.estado.upper())
        return respuesta_error(
            409,
            etiqueta,
            f"{nombre} no puede acreditarse. Estado: {inscripcion.estado}.",
            inscripcion.estado,
        )

    inscripcion.estado = "validado"
    inscripcion.validado_en = datetime.utcnow()
    inscripcion.validado_por = request.session.get(
        "usuario_nombre", "Acreditación"
    )
    inscripcion.motivo_no_habilitado = None
    db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "codigo": "validado",
            "titulo": "VALIDADO",
            "mensaje": "Habilitado para sorteo.",
            "jinete": nombre,
            "categoria": categoria_nombre,
            "hora": inscripcion.validado_en.strftime("%H:%M"),
        }
    )
