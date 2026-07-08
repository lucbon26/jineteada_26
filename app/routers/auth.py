from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import verify_password
from app.models.usuario import Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_form(request: Request):
    """Muestra la pantalla de inicio de sesión."""
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None}
    )


@router.post("/login")
def login_submit(
    request: Request,
    usuario: str = Form(...),
    password: str = Form(...)
):
    """Valida usuario y contraseña e inicia sesión."""

    db: Session = SessionLocal()

    try:
        user = db.query(Usuario).filter(
            Usuario.usuario == usuario,
            Usuario.activo == True
        ).first()

        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                request,
                "login.html",
                {"error": "Usuario o contraseña incorrectos"}
            )

        request.session["usuario_id"] = user.id
        request.session["usuario_nombre"] = user.nombre
        request.session["usuario_rol"] = user.rol

        return RedirectResponse("/", status_code=303)

    finally:
        db.close()


@router.get("/logout")
def logout(request: Request):
    """Cierra la sesión actual."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)