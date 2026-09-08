from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria, CategoriaGlobal


router = APIRouter(prefix="/categorias", tags=["Categorías"])
templates = Jinja2Templates(directory="app/templates")


def obtener_campeonato_o_404(campeonato_id: int, db: Session) -> Campeonato:
    campeonato = db.get(Campeonato, campeonato_id)
    if campeonato is None:
        raise HTTPException(status_code=404, detail="Campeonato no encontrado")
    return campeonato


def obtener_categoria_o_404(categoria_id: int, db: Session) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return categoria


def obtener_global_por_nombre(nombre: str, db: Session) -> CategoriaGlobal | None:
    return db.scalar(
        select(CategoriaGlobal).where(
            func.lower(CategoriaGlobal.nombre) == nombre.strip().lower()
        )
    )


def validar_datos(
    nombre: str,
    cantidad_montas: int,
    edad_minima: int | None,
    edad_maxima: int | None,
    peso_minimo: Decimal | None,
    peso_maximo: Decimal | None,
):
    if not nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    if cantidad_montas < 1:
        raise HTTPException(status_code=400, detail="La cantidad de montas debe ser mayor a cero")
    if edad_minima is not None and edad_maxima is not None and edad_minima > edad_maxima:
        raise HTTPException(status_code=400, detail="La edad mínima no puede superar la edad máxima")
    if peso_minimo is not None and peso_maximo is not None and peso_minimo > peso_maximo:
        raise HTTPException(status_code=400, detail="El peso mínimo no puede superar el peso máximo")


@router.get("/nueva/{campeonato_id}", response_class=HTMLResponse)
def formulario_nueva_categoria(
    campeonato_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    campeonato = obtener_campeonato_o_404(campeonato_id, db)
    return templates.TemplateResponse(
        request=request,
        name="categorias/formulario.html",
        context={
            "accion": "Nueva",
            "categoria": None,
            "campeonato": campeonato,
            "categoria_existente": None,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get("usuario_nombre", "Administrador"),
        },
    )


@router.post("/nueva/{campeonato_id}")
def crear_categoria(
    campeonato_id: int,
    request: Request,
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
    usar_existente: str | None = Form(None),
    db: Session = Depends(get_db),
):
    campeonato = obtener_campeonato_o_404(campeonato_id, db)
    nombre_limpio = nombre.strip()
    validar_datos(nombre_limpio, cantidad_montas, edad_minima, edad_maxima, peso_minimo, peso_maximo)

    global_existente = obtener_global_por_nombre(nombre_limpio, db)

    if global_existente is not None:
        ya_asociada = db.scalar(
            select(Categoria).where(
                Categoria.campeonato_id == campeonato_id,
                Categoria.categoria_global_id == global_existente.id,
            )
        )
        if ya_asociada is not None:
            raise HTTPException(
                status_code=409,
                detail=f'La categoría "{global_existente.nombre}" ya está agregada a este campeonato.',
            )

        if usar_existente != "1":
            ejemplo = db.scalar(
                select(Categoria)
                .where(Categoria.categoria_global_id == global_existente.id)
                .order_by(Categoria.id.desc())
            )
            return templates.TemplateResponse(
                request=request,
                name="categorias/reutilizar.html",
                context={
                    "campeonato": campeonato,
                    "categoria_global": global_existente,
                    "categoria_ejemplo": ejemplo,
                    "menu_activo": "campeonatos",
                    "usuario_nombre": request.session.get("usuario_nombre", "Administrador"),
                },
            )

        # Reutilizar: crea la configuración de ESTE campeonato copiando la última
        # configuración conocida de la categoría global.
        ejemplo = db.scalar(
            select(Categoria)
            .where(Categoria.categoria_global_id == global_existente.id)
            .order_by(Categoria.id.desc())
        )
        categoria = Categoria(
            campeonato_id=campeonato.id,
            categoria_global_id=global_existente.id,
            nombre=global_existente.nombre,
            descripcion=ejemplo.descripcion if ejemplo else None,
            orden=ejemplo.orden if ejemplo else 10,
            activa=True,
            puntua_campeonato=ejemplo.puntua_campeonato if ejemplo else True,
            cantidad_montas=ejemplo.cantidad_montas if ejemplo else 1,
            tipo_monta=ejemplo.tipo_monta if ejemplo else None,
            edad_minima=ejemplo.edad_minima if ejemplo else None,
            edad_maxima=ejemplo.edad_maxima if ejemplo else None,
            peso_minimo=ejemplo.peso_minimo if ejemplo else None,
            peso_maximo=ejemplo.peso_maximo if ejemplo else None,
            reglamento=ejemplo.reglamento if ejemplo else None,
        )
    else:
        categoria_global = CategoriaGlobal(nombre=nombre_limpio)
        db.add(categoria_global)
        db.flush()

        categoria = Categoria(
            campeonato_id=campeonato.id,
            categoria_global_id=categoria_global.id,
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
    request.session["flash_success"] = f'Categoría "{categoria.nombre}" agregada al campeonato.'
    return RedirectResponse(f"/campeonatos/{campeonato.id}", status_code=303)


@router.get("/{categoria_id}/editar", response_class=HTMLResponse)
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
            "categoria_existente": None,
            "menu_activo": "campeonatos",
            "usuario_nombre": request.session.get("usuario_nombre", "Administrador"),
        },
    )


@router.post("/{categoria_id}/editar")
def editar_categoria(
    categoria_id: int,
    request: Request,
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
    categoria = obtener_categoria_o_404(categoria_id, db)
    nombre_limpio = nombre.strip()
    validar_datos(nombre_limpio, cantidad_montas, edad_minima, edad_maxima, peso_minimo, peso_maximo)

    global_obj = categoria.categoria_global
    if global_obj is None or global_obj.nombre.lower() != nombre_limpio.lower():
        otro_global = obtener_global_por_nombre(nombre_limpio, db)
        if otro_global is not None and (global_obj is None or otro_global.id != global_obj.id):
            raise HTTPException(
                status_code=409,
                detail=f'La categoría global "{otro_global.nombre}" ya existe. Para usarla, agregala como categoría existente.',
            )
        if global_obj is None:
            global_obj = CategoriaGlobal(nombre=nombre_limpio)
            db.add(global_obj)
            db.flush()
            categoria.categoria_global_id = global_obj.id
        else:
            global_obj.nombre = nombre_limpio

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

    request.session["flash_success"] = "Categoría actualizada."
    return RedirectResponse(f"/campeonatos/{categoria.campeonato_id}", status_code=303)


@router.post("/{categoria_id}/eliminar")
def eliminar_categoria(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    categoria = obtener_categoria_o_404(categoria_id, db)
    campeonato_id = categoria.campeonato_id

    # Se elimina sólo la configuración/asociación de este campeonato.
    # El nombre global queda disponible para reutilizar en otros campeonatos.
    db.delete(categoria)
    db.commit()
    request.session["flash_success"] = "Categoría quitada del campeonato."
    return RedirectResponse(f"/campeonatos/{campeonato_id}", status_code=303)
