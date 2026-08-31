from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tropilla import Tropilla
from app.models.caballo import Caballo


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/tropillas",
    tags=["Tropillas"],
)


def obtener_tropilla_o_404(
    tropilla_id: int,
    db: Session,
) -> Tropilla:
    tropilla = db.get(Tropilla, tropilla_id)

    if tropilla is None:
        raise HTTPException(
            status_code=404,
            detail="Tropilla no encontrada",
        )

    return tropilla


@router.get("", response_class=HTMLResponse)
def listar_tropillas(
    request: Request,
    buscar: str = Query(default=""),
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db),
):
    consulta = select(Tropilla)

    texto = buscar.strip()

    if texto:
        patron = f"%{texto}%"

        consulta = consulta.where(
            or_(
                Tropilla.nombre.ilike(patron),
                Tropilla.propietario.ilike(patron),
                Tropilla.localidad.ilike(patron),
            )
        )

    if estado == "activas":
        consulta = consulta.where(Tropilla.activo.is_(True))

    elif estado == "inactivas":
        consulta = consulta.where(Tropilla.activo.is_(False))

    consulta = consulta.order_by(Tropilla.nombre.asc())

    tropillas = db.scalars(consulta).all()

    return templates.TemplateResponse(
        request=request,
        name="tropillas/listado.html",
        context={
            "tropillas": tropillas,
            "buscar": buscar,
            "estado": estado,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.get("/nueva", response_class=HTMLResponse)
def formulario_nueva_tropilla(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="tropillas/formulario.html",
        context={
            "tropilla": None,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/nueva")
def crear_tropilla(
    nombre: str = Form(...),
    propietario: str = Form(""),
    localidad: str = Form(""),
    provincia: str = Form(""),
    observaciones: str = Form(""),
    activo: str | None = Form(None),
    db: Session = Depends(get_db),
):
    nombre_limpio = nombre.strip()

    existente = db.scalar(
        select(Tropilla).where(
            Tropilla.nombre == nombre_limpio
        )
    )

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una tropilla con ese nombre",
        )

    tropilla = Tropilla(
        nombre=nombre_limpio,
        propietario=propietario.strip() or None,
        localidad=localidad.strip() or None,
        provincia=provincia.strip() or None,
        observaciones=observaciones.strip() or None,
        activo=activo is not None,
    )

    db.add(tropilla)
    db.commit()
    db.refresh(tropilla)

    return RedirectResponse(
        url="/tropillas",
        status_code=303,
    )



@router.post("/eliminar-masivo")
async def eliminar_tropillas_masivo(
    request: Request,
    db: Session = Depends(get_db),
):
    formulario = await request.form()
    ids = []
    for valor in formulario.getlist("seleccionados"):
        try:
            ids.append(int(valor))
        except (TypeError, ValueError):
            pass

    ids = list(dict.fromkeys(ids))
    eliminados = 0
    omitidos = 0

    for tropilla_id in ids:
        tropilla = db.get(Tropilla, tropilla_id)
        if tropilla is None:
            continue

        caballo_asociado = db.scalar(
            select(Caballo.id)
            .where(Caballo.tropilla_id == tropilla_id)
            .limit(1)
        )

        if caballo_asociado is not None:
            omitidos += 1
            continue

        db.delete(tropilla)
        eliminados += 1

    db.commit()
    return RedirectResponse(
        url=f"/tropillas?eliminados={eliminados}&omitidos={omitidos}",
        status_code=303,
    )


@router.get("/{tropilla_id}/editar", response_class=HTMLResponse)
def formulario_editar_tropilla(
    tropilla_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    tropilla = obtener_tropilla_o_404(tropilla_id, db)

    return templates.TemplateResponse(
        request=request,
        name="tropillas/formulario.html",
        context={
            "tropilla": tropilla,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/{tropilla_id}/editar")
def editar_tropilla(
    tropilla_id: int,
    nombre: str = Form(...),
    propietario: str = Form(""),
    localidad: str = Form(""),
    provincia: str = Form(""),
    observaciones: str = Form(""),
    activo: str | None = Form(None),
    db: Session = Depends(get_db),
):
    tropilla = obtener_tropilla_o_404(tropilla_id, db)

    nombre_limpio = nombre.strip()

    existente = db.scalar(
        select(Tropilla).where(
            Tropilla.nombre == nombre_limpio,
            Tropilla.id != tropilla_id,
        )
    )

    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe otra tropilla con ese nombre",
        )

    tropilla.nombre = nombre_limpio
    tropilla.propietario = propietario.strip() or None
    tropilla.localidad = localidad.strip() or None
    tropilla.provincia = provincia.strip() or None
    tropilla.observaciones = observaciones.strip() or None
    tropilla.activo = activo is not None

    db.commit()

    return RedirectResponse(
        url="/tropillas",
        status_code=303,
    )