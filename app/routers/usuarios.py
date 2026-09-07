from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.permissions import MASTER_USUARIO, ROLES, normalizar_rol
from app.core.security import hash_password
from app.models.usuario import Usuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
templates = Jinja2Templates(directory="app/templates")


def _master(request: Request) -> bool:
    return normalizar_rol(request.session.get("usuario_rol")) == "MASTER"


def _redir(mensaje: str = "", error: str = ""):
    from urllib.parse import urlencode
    q = urlencode({k: v for k, v in {"mensaje": mensaje, "error": error}.items() if v})
    return RedirectResponse(f"/usuarios?{q}" if q else "/usuarios", status_code=303)


@router.get("")
def listado(request: Request, mensaje: str = "", error: str = ""):
    if not _master(request):
        return RedirectResponse("/", status_code=303)
    db: Session = SessionLocal()
    try:
        usuarios = db.query(Usuario).order_by(Usuario.id.asc()).all()
        return templates.TemplateResponse(request, "usuarios/listado.html", {
            "usuarios": usuarios, "roles": sorted(ROLES - {"MASTER"}),
            "menu_activo": "usuarios", "mensaje": mensaje, "error": error,
            "master_usuario": MASTER_USUARIO,
        })
    finally:
        db.close()


@router.post("/nuevo")
def nuevo(nombre: str = Form(...), usuario: str = Form(...), password: str = Form(...), rol: str = Form(...)):
    db: Session = SessionLocal()
    try:
        rol = normalizar_rol(rol)
        usuario = usuario.strip()
        if rol not in ROLES - {"MASTER"}:
            return _redir(error="Rol inválido.")
        if len(password) < 6:
            return _redir(error="La contraseña debe tener al menos 6 caracteres.")
        if db.query(Usuario).filter(Usuario.usuario == usuario).first():
            return _redir(error="Ese nombre de usuario ya existe.")
        db.add(Usuario(nombre=nombre.strip(), usuario=usuario, password_hash=hash_password(password), rol=rol, activo=True))
        db.commit()
        return _redir(mensaje="Usuario creado correctamente.")
    finally:
        db.close()


@router.post("/{usuario_id}/editar")
def editar(usuario_id: int, nombre: str = Form(...), rol: str = Form(...)):
    db: Session = SessionLocal()
    try:
        user = db.get(Usuario, usuario_id)
        if not user:
            return _redir(error="Usuario inexistente.")
        if user.usuario == MASTER_USUARIO:
            return _redir(error="El usuario MASTER está protegido.")
        rol = normalizar_rol(rol)
        if rol not in ROLES - {"MASTER"}:
            return _redir(error="Rol inválido.")
        user.nombre = nombre.strip()
        user.rol = rol
        db.commit()
        return _redir(mensaje="Usuario actualizado.")
    finally:
        db.close()


@router.post("/{usuario_id}/estado")
def estado(usuario_id: int):
    db: Session = SessionLocal()
    try:
        user = db.get(Usuario, usuario_id)
        if not user:
            return _redir(error="Usuario inexistente.")
        if user.usuario == MASTER_USUARIO:
            return _redir(error="El usuario MASTER no se puede desactivar.")
        user.activo = not user.activo
        db.commit()
        return _redir(mensaje="Estado del usuario actualizado.")
    finally:
        db.close()


@router.post("/{usuario_id}/password")
def cambiar_password(usuario_id: int, password: str = Form(...)):
    db: Session = SessionLocal()
    try:
        user = db.get(Usuario, usuario_id)
        if not user:
            return _redir(error="Usuario inexistente.")
        if user.usuario == MASTER_USUARIO:
            return _redir(error="La contraseña del MASTER no se modifica desde este panel.")
        if len(password) < 6:
            return _redir(error="La contraseña debe tener al menos 6 caracteres.")
        user.password_hash = hash_password(password)
        db.commit()
        return _redir(mensaje="Contraseña restablecida.")
    finally:
        db.close()


@router.post("/{usuario_id}/eliminar")
def eliminar(usuario_id: int):
    db: Session = SessionLocal()
    try:
        user = db.get(Usuario, usuario_id)
        if not user:
            return _redir(error="Usuario inexistente.")
        if user.usuario == MASTER_USUARIO:
            return _redir(error="El usuario MASTER no se puede eliminar.")
        db.delete(user)
        db.commit()
        return _redir(mensaje="Usuario eliminado.")
    finally:
        db.close()
