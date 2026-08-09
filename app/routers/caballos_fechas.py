from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.caballo import Caballo
from app.models.caballo_fecha import CaballoFecha
from app.models.categoria import Categoria
from app.models.fecha import Fecha


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    tags=["Caballos por fecha"],
)


def obtener_fecha_o_404(
    fecha_id: int,
    db: Session,
) -> Fecha:
    fecha = db.get(Fecha, fecha_id)

    if fecha is None:
        raise HTTPException(
            status_code=404,
            detail="Fecha no encontrada",
        )

    return fecha


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
    "/fechas/{fecha_id}/categorias/{categoria_id}/caballos",
    response_class=HTMLResponse,
)
def administrar_caballos_categoria(
    fecha_id: int,
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    fecha = obtener_fecha_o_404(fecha_id, db)
    categoria = obtener_categoria_o_404(categoria_id, db)

    # Evita asociar a una fecha una categoría
    # perteneciente a otro campeonato.
    if categoria.campeonato_id != fecha.campeonato_id:
        raise HTTPException(
            status_code=400,
            detail="La categoría no pertenece al campeonato de esta fecha",
        )

    caballos_ocupados_en_otras_categorias = db.scalars(
    select(CaballoFecha.caballo_id).where(
        CaballoFecha.fecha_id == fecha_id,
        CaballoFecha.categoria_id != categoria_id,
    )
    ).all()

    consulta_caballos = (
        select(Caballo)
        .where(Caballo.estado == "activo")
    )

    if caballos_ocupados_en_otras_categorias:
        consulta_caballos = consulta_caballos.where(
            Caballo.id.not_in(
                caballos_ocupados_en_otras_categorias
            )
        )

    consulta_caballos = consulta_caballos.order_by(
        Caballo.nombre.asc()
    )

    caballos = db.scalars(
        consulta_caballos
    ).all()

    asignaciones = db.scalars(
        select(CaballoFecha).where(
            CaballoFecha.fecha_id == fecha_id,
            CaballoFecha.categoria_id == categoria_id,
        )
    ).all()

    caballos_asignados = {
        asignacion.caballo_id
        for asignacion in asignaciones
    }

    return templates.TemplateResponse(
        request=request,
        name="caballos/asignacion.html",
        context={
            "fecha_evento": fecha,
            "categoria": categoria,
            "campeonato": fecha.campeonato,
            "caballos": caballos,
            "caballos_asignados": caballos_asignados,
            "menu_activo": "caballos",
            "usuario_nombre": request.session.get(
                "usuario_nombre",
                "Administrador",
            ),
        },
    )


@router.post(
    "/fechas/{fecha_id}/categorias/{categoria_id}/caballos"
)
def guardar_caballos_categoria(
    fecha_id: int,
    categoria_id: int,
    caballo_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    fecha = obtener_fecha_o_404(fecha_id, db)
    categoria = obtener_categoria_o_404(categoria_id, db)

    if categoria.campeonato_id != fecha.campeonato_id:
        raise HTTPException(
            status_code=400,
            detail="La categoría no pertenece al campeonato de esta fecha",
        )

    # Borra la selección anterior para esta fecha/categoría.
    db.execute(
        delete(CaballoFecha).where(
            CaballoFecha.fecha_id == fecha_id,
            CaballoFecha.categoria_id == categoria_id,
        )
    )

    # Guarda la nueva selección.
    for caballo_id in caballo_ids:
        caballo = db.get(Caballo, caballo_id)

        if caballo is None:
            continue

        asignacion = CaballoFecha(
            caballo_id=caballo_id,
            fecha_id=fecha_id,
            categoria_id=categoria_id,
        )

        db.add(asignacion)

    db.commit()

    return RedirectResponse(
        url=f"/fechas/{fecha_id}",
        status_code=303,
    )