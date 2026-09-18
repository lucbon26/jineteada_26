from datetime import date
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.fecha import Fecha
from app.core.database import get_db
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria


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


def usuario_es_master(request: Request) -> bool:
    return str(request.session.get("usuario_rol") or "").upper() == "MASTER"


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
  
            "menu_activo": "campeonatos",
        "usuario_nombre": request.session.get(
            "usuario_nombre",
            "Administrador",
            
        ),
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
    modo_prueba: str | None = Form(None),
    informacion_publica: str = Form(""),
    reglamento_publico: str = Form(""),
    documento_url: str = Form(""),
    publicado: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    Crea un campeonato nuevo.
    """

    if not usuario_autenticado(request):
        return RedirectResponse("/login", status_code=303)

    documento_url = documento_url.strip()
    if documento_url and (urlparse(documento_url).scheme != "https" or not urlparse(documento_url).netloc or len(documento_url) > 500):
        raise HTTPException(status_code=400, detail="El documento debe tener un enlace HTTPS válido de hasta 500 caracteres.")
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
        informacion_publica=informacion_publica.strip() or None,
        reglamento_publico=reglamento_publico.strip() or None,
        documento_url=documento_url or None,
        publicado=publicado,
        fecha_inicio=fecha_inicio_convertida,
        fecha_fin=fecha_fin_convertida,
        estado=estado,
        modo_prueba=(modo_prueba == "1"),
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
    modo_prueba: str | None = Form(None),
    informacion_publica: str = Form(""),
    reglamento_publico: str = Form(""),
    documento_url: str = Form(""),
    publicado: bool = Form(False),
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

    documento_url = documento_url.strip()
    if documento_url and (urlparse(documento_url).scheme != "https" or not urlparse(documento_url).netloc or len(documento_url) > 500):
        raise HTTPException(status_code=400, detail="El documento debe tener un enlace HTTPS válido de hasta 500 caracteres.")
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
    campeonato.informacion_publica = informacion_publica.strip() or None
    campeonato.reglamento_publico = reglamento_publico.strip() or None
    campeonato.documento_url = documento_url or None
    campeonato.publicado = publicado
    campeonato.fecha_inicio = fecha_inicio_convertida
    campeonato.fecha_fin = fecha_fin_convertida
    campeonato.estado = estado
    campeonato.modo_prueba = (modo_prueba == "1")

    db.commit()

    return RedirectResponse(
        "/campeonatos",
        status_code=303,
    )


@router.post("/{campeonato_id}/eliminar")
def eliminar_campeonato(campeonato_id: int, request: Request, db: Session = Depends(get_db)):
    from app.services.eliminacion import exigir_borrado, borrar_campeonato
    exigir_borrado(request)
    if db.get(Campeonato, campeonato_id) is None:
        return RedirectResponse('/campeonatos', status_code=303)
    borrar_campeonato(db, campeonato_id)
    db.commit()
    request.session['flash_success'] = 'Campeonato eliminado. Los padrones de jinetes y caballos se conservaron.'
    return RedirectResponse('/campeonatos', status_code=303)



@router.get("/{campeonato_id}", response_class=HTMLResponse)
def detalle_campeonato(
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

    fechas = (
        db.query(Fecha)
        .filter(Fecha.campeonato_id == campeonato_id)
        .order_by(Fecha.fecha.asc())
        .all()
    )
    
    categorias = (
        db.query(Categoria)
        .filter(
            Categoria.campeonato_id == campeonato_id
        )
        .order_by(
            Categoria.orden.asc(),
            Categoria.nombre.asc(),
        )
        .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="campeonatos/detalle.html",
        context={
            "campeonato": campeonato,
            "fechas": fechas,
            "categorias": categorias,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )
    
    