from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import verify_password
from app.models.usuario import Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def destino_seguro(valor: str | None) -> str:
    destino = (valor or "/").strip()
    if not destino.startswith("/") or destino.startswith("//"):
        return "/"
    return destino


@router.get("/login")
def login_form(request: Request, next: str = "/"):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": None,
            "next": destino_seguro(next),
        },
    )


@router.post("/login")
def login_submit(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    db: Session = SessionLocal()

    try:
        user = db.query(Usuario).filter(
            Usuario.usuario == usuario,
            Usuario.activo == True,
        ).first()

        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    "error": "Usuario o contraseña incorrectos",
                    "next": destino_seguro(next),
                },
            )

        request.session["usuario_id"] = user.id
        request.session["usuario_nombre"] = user.nombre
        request.session["usuario_rol"] = user.rol

        # Volver a la página solicitada antes del login.
        destino = destino_seguro(next)

        # Un usuario de rol Acreditación siempre entra en su pantalla.
        rol = str(user.rol or "").strip().lower()
        if rol in {"acreditación", "acreditacion"}:
            destino = "/acreditacion"

        return RedirectResponse(destino, status_code=303)

    finally:
        db.close()


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
