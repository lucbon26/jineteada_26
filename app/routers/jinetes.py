from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.core.database import get_db
from app.models.jinete import Jinete

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/jinetes",
    tags=["Jinetes"],
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