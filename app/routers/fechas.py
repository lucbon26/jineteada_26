from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campeonato import Campeonato
from app.models.fecha import Fecha


router = APIRouter(
    prefix="/fechas",
    tags=["Fechas"],
)

templates = Jinja2Templates(directory="app/templates")


def obtener_fecha_o_404(
    fecha_id: int,
    db: Session,
) -> Fecha:
    fecha_evento = (
        db.query(Fecha)
        .filter(Fecha.id == fecha_id)
        .first()
    )

    if fecha_evento is None:
        raise HTTPException(
            status_code=404,
            detail="Fecha no encontrada",
        )

    return fecha_evento


@router.get("/{fecha_id}", response_class=HTMLResponse)
def detalle_fecha(
    fecha_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    fecha_evento = obtener_fecha_o_404(fecha_id, db)

    return templates.TemplateResponse(
        request=request,
        name="fechas/detalle.html",
        context={
            "fecha_evento": fecha_evento,
            "campeonato": fecha_evento.campeonato,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.get(
    "/nueva/{campeonato_id}",
    response_class=HTMLResponse,
)
def formulario_nueva_fecha(
    campeonato_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    campeonato = (
        db.query(Campeonato)
        .filter(Campeonato.id == campeonato_id)
        .first()
    )

    if campeonato is None:
        raise HTTPException(
            status_code=404,
            detail="Campeonato no encontrado",
        )

    return templates.TemplateResponse(
        request=request,
        name="fechas/formulario.html",
        context={
            "accion": "Nueva",
            "campeonato": campeonato,
            "fecha_evento": None,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/nueva/{campeonato_id}")
def crear_fecha(
    campeonato_id: int,
    nombre: str = Form(...),
    fecha: date = Form(...),
    localidad: str = Form(...),
    provincia: str = Form(""),
    lugar: str = Form(""),
    organizador: str = Form(""),
    estado: str = Form("programada"),
    observaciones: str = Form(""),
    db: Session = Depends(get_db),
):
    campeonato = (
        db.query(Campeonato)
        .filter(Campeonato.id == campeonato_id)
        .first()
    )

    if campeonato is None:
        raise HTTPException(
            status_code=404,
            detail="Campeonato no encontrado",
        )

    nueva_fecha = Fecha(
        campeonato_id=campeonato_id,
        nombre=nombre.strip(),
        fecha=fecha,
        localidad=localidad.strip(),
        provincia=provincia.strip() or None,
        lugar=lugar.strip() or None,
        organizador=organizador.strip() or None,
        estado=estado,
        observaciones=observaciones.strip() or None,
    )

    db.add(nueva_fecha)
    db.commit()
    db.refresh(nueva_fecha)

    return RedirectResponse(
        url=f"/fechas/{nueva_fecha.id}",
        status_code=303,
    )


@router.get(
    "/{fecha_id}/editar",
    response_class=HTMLResponse,
)
def formulario_editar_fecha(
    fecha_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    fecha_evento = obtener_fecha_o_404(fecha_id, db)

    return templates.TemplateResponse(
        request=request,
        name="fechas/formulario.html",
        context={
            "accion": "Editar",
            "campeonato": fecha_evento.campeonato,
            "fecha_evento": fecha_evento,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/{fecha_id}/editar")
def editar_fecha(
    fecha_id: int,
    nombre: str = Form(...),
    fecha: date = Form(...),
    localidad: str = Form(...),
    provincia: str = Form(""),
    lugar: str = Form(""),
    organizador: str = Form(""),
    estado: str = Form("programada"),
    observaciones: str = Form(""),
    db: Session = Depends(get_db),
):
    fecha_evento = obtener_fecha_o_404(fecha_id, db)

    fecha_evento.nombre = nombre.strip()
    fecha_evento.fecha = fecha
    fecha_evento.localidad = localidad.strip()
    fecha_evento.provincia = provincia.strip() or None
    fecha_evento.lugar = lugar.strip() or None
    fecha_evento.organizador = organizador.strip() or None
    fecha_evento.estado = estado
    fecha_evento.observaciones = observaciones.strip() or None

    db.commit()

    return RedirectResponse(
        url=f"/fechas/{fecha_evento.id}",
        status_code=303,
    )


@router.post("/{fecha_id}/eliminar")
def eliminar_fecha(
    fecha_id: int,
    db: Session = Depends(get_db),
):
    fecha_evento = obtener_fecha_o_404(fecha_id, db)
    campeonato_id = fecha_evento.campeonato_id

    db.delete(fecha_evento)
    db.commit()

    return RedirectResponse(
        url=f"/campeonatos/{campeonato_id}",
        status_code=303,
    )