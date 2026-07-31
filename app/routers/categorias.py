from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session

from app.models.campeonato import Campeonato
from decimal import Decimal
from app.core.database import get_db
from app.models.categoria import Categoria
from app.models.fecha import Fecha


router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"],
)

templates = Jinja2Templates(directory="app/templates")

def obtener_campeonato_o_404(
    campeonato_id: int,
    db: Session,
) -> Campeonato:
    campeonato = db.get(Campeonato, campeonato_id)

    if campeonato is None:
        raise HTTPException(
            status_code=404,
            detail="Campeonato no encontrado",
        )

    return campeonato


def obtener_fecha_o_404(
    fecha_id: int,
    db: Session,
) -> Fecha:
    fecha_evento = db.get(Fecha, fecha_id)

    if fecha_evento is None:
        raise HTTPException(
            status_code=404,
            detail="Fecha no encontrada",
        )

    return fecha_evento


def obtener_categoria_o_404(
    categoria_id: int,
    db: Session,
) -> Categoria:
    categoria = db.get(Categoria, categoria_id)

    if categoria is None:
        raise HTTPException(
            status_code=404,
            detail="Categoría no encontrada",
        )

    return categoria


@router.get(
    "/nueva/{fecha_id}",
    response_class=HTMLResponse,
)
def formulario_nueva_categoria(
    fecha_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    fecha_evento = obtener_fecha_o_404(fecha_id, db)

    return templates.TemplateResponse(
        request=request,
        name="categorias/formulario.html",
        context={
            "accion": "Nueva",
            "categoria": None,
            "fecha_evento": fecha_evento,
            "campeonato": fecha_evento.campeonato,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/nueva/{campeonato_id}")
def crear_categoria(
    campeonato_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    orden: int = Form(10),
    activa: str | None = Form(None),
    puntua_campeonato: str | None = Form(None),
    cantidad_montas: int = Form(1),
    tipo_monta: str = Form(""),
    edad_minima: int | None = Form(None),
    edad_maxima: int | None = Form(None),
    peso_minimo: Decimal | None = Form(None),
    peso_maximo: Decimal | None = Form(None),
    reglamento: str = Form(""),
    db: Session = Depends(get_db),
):
    campeonato = obtener_campeonato_o_404(
        campeonato_id,
        db,
    )

    nombre_limpio = nombre.strip()

    if not nombre_limpio:
        raise HTTPException(
            status_code=400,
            detail="El nombre es obligatorio",
        )

    if cantidad_montas < 1:
        raise HTTPException(
            status_code=400,
            detail="La cantidad de montas debe ser mayor a cero",
        )

    if (
        edad_minima is not None
        and edad_maxima is not None
        and edad_minima > edad_maxima
    ):
        raise HTTPException(
            status_code=400,
            detail="La edad mínima no puede superar la edad máxima",
        )

    if (
        peso_minimo is not None
        and peso_maximo is not None
        and peso_minimo > peso_maximo
    ):
        raise HTTPException(
            status_code=400,
            detail="El peso mínimo no puede superar el peso máximo",
        )

    consulta = select(Categoria).where(
        Categoria.campeonato_id == campeonato.id,
        Categoria.nombre == nombre_limpio,
    )

    if db.scalar(consulta) is not None:
        raise HTTPException(
            status_code=400,
            detail="La categoría ya existe en este campeonato",
        )

    categoria = Categoria(
        campeonato_id=campeonato.id,
        nombre=nombre_limpio,
        descripcion=descripcion.strip() or None,
        orden=orden,
        activa=activa == "on",
        puntua_campeonato=puntua_campeonato == "on",
        cantidad_montas=cantidad_montas,
        tipo_monta=tipo_monta.strip() or None,
        edad_minima=edad_minima,
        edad_maxima=edad_maxima,
        peso_minimo=peso_minimo,
        peso_maximo=peso_maximo,
        reglamento=reglamento.strip() or None,
    )

    db.add(categoria)
    db.commit()
    db.refresh(categoria)

    return RedirectResponse(
        url=f"/campeonatos/{campeonato.id}",
        status_code=303,
    )


@router.get(
    "/{categoria_id}/editar",
    response_class=HTMLResponse,
)
def formulario_editar_categoria(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    categoria = obtener_categoria_o_404(categoria_id, db)

    return templates.TemplateResponse(
        request=request,
        name="categorias/formulario.html",
        context={
            "accion": "Editar",
            "categoria": categoria,
            "campeonato": categoria.campeonato,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post("/{categoria_id}/editar")
def editar_categoria(
    categoria_id: int,
    nombre: str = Form(...),
    descripcion: str = Form(""),
    orden: int = Form(10),
    activa: str | None = Form(None),
    puntua_campeonato: str | None = Form(None),
    cantidad_montas: int = Form(1),
    tipo_monta: str = Form(""),
    edad_minima: int | None = Form(None),
    edad_maxima: int | None = Form(None),
    peso_minimo: Decimal | None = Form(None),
    peso_maximo: Decimal | None = Form(None),
    reglamento: str = Form(""),
    db: Session = Depends(get_db),
):
    categoria = obtener_categoria_o_404(
        categoria_id,
        db,
    )

    nombre_limpio = nombre.strip()

    if not nombre_limpio:
        raise HTTPException(
            status_code=400,
            detail="El nombre es obligatorio",
        )

    if cantidad_montas < 1:
        raise HTTPException(
            status_code=400,
            detail="La cantidad de montas debe ser mayor a cero",
        )

    if (
        edad_minima is not None
        and edad_maxima is not None
        and edad_minima > edad_maxima
    ):
        raise HTTPException(
            status_code=400,
            detail="La edad mínima no puede superar la edad máxima",
        )

    if (
        peso_minimo is not None
        and peso_maximo is not None
        and peso_minimo > peso_maximo
    ):
        raise HTTPException(
            status_code=400,
            detail="El peso mínimo no puede superar el peso máximo",
        )

    consulta = select(Categoria).where(
        Categoria.campeonato_id == categoria.campeonato_id,
        Categoria.nombre == nombre_limpio,
        Categoria.id != categoria.id,
    )

    if db.scalar(consulta) is not None:
        raise HTTPException(
            status_code=400,
            detail="La categoría ya existe en este campeonato",
        )

    categoria.nombre = nombre_limpio
    categoria.descripcion = descripcion.strip() or None
    categoria.orden = orden
    categoria.activa = activa == "on"
    categoria.puntua_campeonato = puntua_campeonato == "on"
    categoria.cantidad_montas = cantidad_montas
    categoria.tipo_monta = tipo_monta.strip() or None
    categoria.edad_minima = edad_minima
    categoria.edad_maxima = edad_maxima
    categoria.peso_minimo = peso_minimo
    categoria.peso_maximo = peso_maximo
    categoria.reglamento = reglamento.strip() or None

    db.commit()

    return RedirectResponse(
        url=f"/campeonatos/{categoria.campeonato_id}",
        status_code=303,
    )

@router.post("/{categoria_id}/eliminar")
def eliminar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
):
    categoria = obtener_categoria_o_404(categoria_id, db)
    fecha_id = categoria.fecha_id

    db.delete(categoria)
    db.commit()

    return RedirectResponse(
        url=f"/fechas/{fecha_id}",
        status_code=303,
    )