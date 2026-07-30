from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campeonato import Campeonato


router = APIRouter(
    prefix="/campeonatos",
    tags=["Campeonatos"],
)

templates = Jinja2Templates(directory="app/templates")

ESTADOS_VALIDOS = {
    "borrador",
    "activo",
    "finalizado",
}


def usuario_autenticado(request: Request) -> bool:
    """
    Verifica si existe una sesión de usuario activa.
    """

    return bool(request.session.get("usuario_id"))


def convertir_fecha(valor: str | None) -> date | None:
    """
    Convierte una fecha recibida desde un formulario HTML.

    Los campos vacíos se guardan como None.
    """

    if not valor:
        return None

    return date.fromisoformat(valor)


@router.get("", response_class=HTMLResponse)
def listar_campeonatos(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Muestra todos los campeonatos registrados.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    consulta = select(Campeonato).order_by(
        Campeonato.creado_en.desc()
    )

    campeonatos = db.scalars(consulta).all()

    return templates.TemplateResponse(
        request=request,
        name="campeonatos/listado.html",
        context={
            "campeonatos": campeonatos,
        },
    )


@router.get("/nuevo", response_class=HTMLResponse)
def formulario_nuevo_campeonato(request: Request):
    """
    Muestra el formulario para crear un campeonato.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="campeonatos/formulario.html",
        context={
            "campeonato": None,
            "accion": "Crear",
            "error": None,
        },
    )


@router.post("/nuevo")
def crear_campeonato(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    fecha_inicio: str = Form(""),
    fecha_fin: str = Form(""),
    estado: str = Form("borrador"),
    db: Session = Depends(get_db),
):
    """
    Crea un campeonato nuevo.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    nombre = nombre.strip()
    descripcion = descripcion.strip()

    if not nombre:
        return templates.TemplateResponse(
            request=request,
            name="campeonatos/formulario.html",
            context={
                "campeonato": None,
                "accion": "Crear",
                "error": "El nombre del campeonato es obligatorio.",
            },
            status_code=400,
        )

    if estado not in ESTADOS_VALIDOS:
        estado = "borrador"

    fecha_inicio_convertida = convertir_fecha(fecha_inicio)
    fecha_fin_convertida = convertir_fecha(fecha_fin)

    if (
        fecha_inicio_convertida
        and fecha_fin_convertida
        and fecha_fin_convertida < fecha_inicio_convertida
    ):
        return templates.TemplateResponse(
            request=request,
            name="campeonatos/formulario.html",
            context={
                "campeonato": None,
                "accion": "Crear",
                "error": (
                    "La fecha de finalización no puede ser anterior "
                    "a la fecha de inicio."
                ),
            },
            status_code=400,
        )

    campeonato = Campeonato(
        nombre=nombre,
        descripcion=descripcion or None,
        fecha_inicio=fecha_inicio_convertida,
        fecha_fin=fecha_fin_convertida,
        estado=estado,
    )

    db.add(campeonato)
    db.commit()

    return RedirectResponse(
        "/campeonatos",
        status_code=303,
    )


@router.get("/{campeonato_id}/editar", response_class=HTMLResponse)
def formulario_editar_campeonato(
    campeonato_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Muestra el formulario de edición de un campeonato.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    campeonato = db.get(Campeonato, campeonato_id)

    if campeonato is None:
        return RedirectResponse(
            "/campeonatos",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="campeonatos/formulario.html",
        context={
            "campeonato": campeonato,
            "accion": "Editar",
            "error": None,
        },
    )


@router.post("/{campeonato_id}/editar")
def editar_campeonato(
    campeonato_id: int,
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    fecha_inicio: str = Form(""),
    fecha_fin: str = Form(""),
    estado: str = Form("borrador"),
    db: Session = Depends(get_db),
):
    """
    Actualiza los datos de un campeonato.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    campeonato = db.get(Campeonato, campeonato_id)

    if campeonato is None:
        return RedirectResponse(
            "/campeonatos",
            status_code=303,
        )

    nombre = nombre.strip()
    descripcion = descripcion.strip()

    if not nombre:
        return templates.TemplateResponse(
            request=request,
            name="campeonatos/formulario.html",
            context={
                "campeonato": campeonato,
                "accion": "Editar",
                "error": "El nombre del campeonato es obligatorio.",
            },
            status_code=400,
        )

    fecha_inicio_convertida = convertir_fecha(fecha_inicio)
    fecha_fin_convertida = convertir_fecha(fecha_fin)

    if (
        fecha_inicio_convertida
        and fecha_fin_convertida
        and fecha_fin_convertida < fecha_inicio_convertida
    ):
        return templates.TemplateResponse(
            request=request,
            name="campeonatos/formulario.html",
            context={
                "campeonato": campeonato,
                "accion": "Editar",
                "error": (
                    "La fecha de finalización no puede ser anterior "
                    "a la fecha de inicio."
                ),
            },
            status_code=400,
        )

    if estado not in ESTADOS_VALIDOS:
        estado = "borrador"

    campeonato.nombre = nombre
    campeonato.descripcion = descripcion or None
    campeonato.fecha_inicio = fecha_inicio_convertida
    campeonato.fecha_fin = fecha_fin_convertida
    campeonato.estado = estado

    db.commit()

    return RedirectResponse(
        "/campeonatos",
        status_code=303,
    )


@router.post("/{campeonato_id}/eliminar")
def eliminar_campeonato(
    campeonato_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Elimina un campeonato.

    Más adelante restringiremos la eliminación cuando tenga
    fechas, inscripciones o resultados asociados.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    campeonato = db.get(Campeonato, campeonato_id)

    if campeonato is not None:
        db.delete(campeonato)
        db.commit()

    return RedirectResponse(
        "/campeonatos",
        status_code=303,
    )