from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.core.database import get_db
from app.models.jinete import Jinete
from datetime import date

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/jinetes",
    tags=["Jinetes"],
)

@router.get(
    "/nuevo",
    response_class=HTMLResponse,
)
def formulario_nuevo_jinete(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="jinetes/formulario.html",
        context={
            "accion": "Nuevo",
            "jinete": None,
            "menu_activo": "jinetes",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )

@router.get("", response_class=HTMLResponse)
def listar_jinetes(
    request: Request,
    buscar: str = Query(default=""),
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db),
):
    consulta = select(Jinete)

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

    if estado != "todos":
        consulta = consulta.where(
        Jinete.estado == estado
    )
    
    consulta = consulta.order_by(
        Jinete.apellidos.asc(),
        Jinete.nombres.asc(),
    )

    jinetes = db.scalars(consulta).all()

    return templates.TemplateResponse(
        request=request,
        name="jinetes/listado.html",
        context={
            "jinetes": jinetes,
            "buscar": buscar,
            "estado": estado,
            "menu_activo": "jinetes",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )

@router.post("/nuevo")
def crear_jinete(
    nombres: str = Form(...),
    apellidos: str = Form(...),
    dni: str = Form(...),
    fecha_nacimiento: date | None = Form(None),
    sexo: str = Form(""),
    nacionalidad: str = Form(""),
    celular: str = Form(""),
    email: str = Form(""),
    provincia: str = Form(""),
    localidad: str = Form(""),
    categoria_habitual: str = Form(""),
    club_agrupacion: str = Form(""),
    observaciones: str = Form(""),
    estado: str = Form("activo"),
    db: Session = Depends(get_db),
):
    dni_limpio = dni.strip()

    jinete_existente = db.scalar(
        select(Jinete).where(Jinete.dni == dni_limpio)
    )

    if jinete_existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un jinete registrado con ese DNI",
        )

    nuevo_jinete = Jinete(
        nombres=nombres.strip(),
        apellidos=apellidos.strip(),
        dni=dni_limpio,
        fecha_nacimiento=fecha_nacimiento,
        sexo=sexo.strip() or None,
        nacionalidad=nacionalidad.strip() or None,
        celular=celular.strip() or None,
        email=email.strip() or None,
        provincia=provincia.strip() or None,
        localidad=localidad.strip() or None,
        categoria_habitual=categoria_habitual.strip() or None,
        club_agrupacion=club_agrupacion.strip() or None,
        observaciones=observaciones.strip() or None,
        estado=estado,
    )

    db.add(nuevo_jinete)
    db.commit()
    db.refresh(nuevo_jinete)

    return RedirectResponse(
        url="/jinetes",
        status_code=303,
    )


    
    
def formulario_nuevo_jinete(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="jinetes/formulario.html",
        context={
            "accion": "Nuevo",
            "jinete": None,
            "menu_activo": "jinetes",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )

@router.get("", response_class=HTMLResponse)
def listar_jinetes(
    request: Request,
    buscar: str = Query(default=""),
    estado: str = Query(default="todos"),
    db: Session = Depends(get_db),
):
    consulta = select(Jinete)

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

    if estado == "activos":
        consulta = consulta.where(Jinete.activo.is_(True))

    elif estado == "inactivos":
        consulta = consulta.where(Jinete.activo.is_(False))

    consulta = consulta.order_by(
        Jinete.apellidos.asc(),
        Jinete.nombres.asc(),
    )

    jinetes = db.scalars(consulta).all()

    return templates.TemplateResponse(
        request=request,
        name="jinetes/listado.html",
        context={
            "jinetes": jinetes,
            "buscar": buscar,
            "estado": estado,
            "menu_activo": "jinetes",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )
    
@router.get(
    "/{jinete_id}",
    response_class=HTMLResponse,
)
def detalle_jinete(
    jinete_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Muestra la ficha individual de un jinete.
    """

    jinete = db.get(Jinete, jinete_id)

    if jinete is None:
        raise HTTPException(
            status_code=404,
            detail="Jinete no encontrado",
        )

    return templates.TemplateResponse(
        request=request,
        name="jinetes/detalle.html",
        context={
            "jinete": jinete,
            "menu_activo": "jinetes",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.get(
    "/{jinete_id}/editar",
    response_class=HTMLResponse,
)
def formulario_editar_jinete(
    jinete_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    jinete = db.get(Jinete, jinete_id)

    if jinete is None:
        raise HTTPException(
            status_code=404,
            detail="Jinete no encontrado",
        )

    return templates.TemplateResponse(
        request=request,
        name="jinetes/formulario.html",
        context={
            "accion": "Editar",
            "jinete": jinete,
            "menu_activo": "jinetes",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )

@router.post("/{jinete_id}/editar")
def editar_jinete(
    jinete_id: int,
    nombres: str = Form(...),
    apellidos: str = Form(...),
    dni: str = Form(...),
    fecha_nacimiento: date | None = Form(None),
    sexo: str = Form(""),
    nacionalidad: str = Form(""),
    celular: str = Form(""),
    email: str = Form(""),
    provincia: str = Form(""),
    localidad: str = Form(""),
    categoria_habitual: str = Form(""),
    club_agrupacion: str = Form(""),
    observaciones: str = Form(""),
    estado: str = Form("activo"),
    db: Session = Depends(get_db),
):
    jinete = db.get(Jinete, jinete_id)

    if jinete is None:
        raise HTTPException(
            status_code=404,
            detail="Jinete no encontrado",
        )

    dni_limpio = dni.strip()

    jinete_con_mismo_dni = db.scalar(
        select(Jinete).where(
            Jinete.dni == dni_limpio,
            Jinete.id != jinete_id,
        )
    )

    if jinete_con_mismo_dni:
        raise HTTPException(
            status_code=400,
            detail="Ya existe otro jinete registrado con ese DNI",
        )

    jinete.nombres = nombres.strip()
    jinete.apellidos = apellidos.strip()
    jinete.dni = dni_limpio
    jinete.fecha_nacimiento = fecha_nacimiento
    jinete.sexo = sexo.strip() or None
    jinete.nacionalidad = nacionalidad.strip() or None
    jinete.celular = celular.strip() or None
    jinete.email = email.strip() or None
    jinete.provincia = provincia.strip() or None
    jinete.localidad = localidad.strip() or None
    jinete.categoria_habitual = categoria_habitual.strip() or None
    jinete.club_agrupacion = club_agrupacion.strip() or None
    jinete.observaciones = observaciones.strip() or None
    jinete.estado = estado

    db.commit()

    return RedirectResponse(
        url=f"/jinetes/{jinete.id}",
        status_code=303,
    )