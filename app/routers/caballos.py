from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.caballo import Caballo
from app.models.tropilla import Tropilla


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/caballos",
    tags=["Caballos"],
)


def obtener_caballo_o_404(
    caballo_id: int,
    db: Session,
) -> Caballo:
    caballo = db.get(Caballo, caballo_id)

    if caballo is None:
        raise HTTPException(
            status_code=404,
            detail="Caballo no encontrado",
        )

    return caballo


@router.get("", response_class=HTMLResponse)
def listar_caballos(
    request: Request,
    buscar: str = Query(default=""),
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db),
):
    consulta = select(Caballo)

    texto = buscar.strip()

    if texto:
        patron = f"%{texto}%"

        consulta = (
            consulta
            .join(Tropilla, Caballo.tropilla_id == Tropilla.id, isouter=True)
            .where(
                or_(
                    Caballo.nombre.ilike(patron),
                    Caballo.pelaje.ilike(patron),
                    Tropilla.nombre.ilike(patron),
                )
            )
        )

    if estado != "todos":
        consulta = consulta.where(
            Caballo.estado == estado
        )

    consulta = consulta.order_by(
        Caballo.nombre.asc()
    )

    caballos = db.scalars(consulta).all()

    return templates.TemplateResponse(
        request=request,
        name="caballos/listado.html",
        context={
            "caballos": caballos,
            "buscar": buscar,
            "estado": estado,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.get("/nuevo", response_class=HTMLResponse)
def formulario_nuevo_caballo(
    request: Request,
    db: Session = Depends(get_db),
):
    tropillas = db.scalars(
        select(Tropilla)
        .where(Tropilla.activo.is_(True))
        .order_by(Tropilla.nombre.asc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="caballos/formulario.html",
        context={
            "caballo": None,
            "tropillas": tropillas,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/nuevo")
def crear_caballo(
    nombre: str = Form(...),
    tropilla_id: int | None = Form(None),
    pelaje: str = Form(""),
    estado: str = Form("activo"),
    observaciones: str = Form(""),
    db: Session = Depends(get_db),
):
    nombre_limpio = nombre.strip()

    caballo = Caballo(
        nombre=nombre_limpio,
        tropilla_id=tropilla_id,
        pelaje=pelaje.strip() or None,
        estado=estado,
        observaciones=observaciones.strip() or None,
    )

    db.add(caballo)
    db.commit()
    db.refresh(caballo)

    return RedirectResponse(
        url="/caballos",
        status_code=303,
    )


@router.get(
    "/{caballo_id}/editar",
    response_class=HTMLResponse,
)
def formulario_editar_caballo(
    caballo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    caballo = obtener_caballo_o_404(
        caballo_id,
        db,
    )

    tropillas = db.scalars(
        select(Tropilla)
        .order_by(Tropilla.nombre.asc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="caballos/formulario.html",
        context={
            "caballo": caballo,
            "tropillas": tropillas,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/{caballo_id}/editar")
def editar_caballo(
    caballo_id: int,
    nombre: str = Form(...),
    tropilla_id: int | None = Form(None),
    pelaje: str = Form(""),
    estado: str = Form("activo"),
    observaciones: str = Form(""),
    db: Session = Depends(get_db),
):
    caballo = obtener_caballo_o_404(
        caballo_id,
        db,
    )

    caballo.nombre = nombre.strip()
    caballo.tropilla_id = tropilla_id
    caballo.pelaje = pelaje.strip() or None
    caballo.estado = estado
    caballo.observaciones = observaciones.strip() or None

    db.commit()

    return RedirectResponse(
        url="/caballos",
        status_code=303,
    )