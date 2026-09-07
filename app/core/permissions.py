from fastapi import Request

ROLES = {"MASTER", "ADMIN", "SECRETARIA", "ACREDITACION", "LOCUCION", "TV"}
MASTER_USUARIO = "admin"


def normalizar_rol(rol: str | None) -> str:
    valor = str(rol or "").strip().upper()
    if valor in {"ACREDITACIÓN", "ACREDITACION"}:
        return "ACREDITACION"
    if valor in {"SECRETARÍA", "SECRETARIA"}:
        return "SECRETARIA"
    if valor in {"LOCUCIÓN", "LOCUCION"}:
        return "LOCUCION"
    return valor


def destino_por_rol(rol: str | None) -> str:
    rol = normalizar_rol(rol)
    if rol == "ACREDITACION":
        return "/acreditacion"
    if rol in {"LOCUCION", "TV"}:
        return "/sorteos"
    return "/"


def acceso_permitido(request: Request) -> bool:
    path = request.url.path
    metodo = request.method.upper()

    if path in {"/login", "/logout"} or path.startswith("/static/") or path.startswith("/publico/"):
        return True

    if not request.session.get("usuario_id"):
        return False

    rol = normalizar_rol(request.session.get("usuario_rol"))

    if rol == "MASTER":
        return True

    if path.startswith("/usuarios"):
        return False

    if rol == "ADMIN":
        return True

    if rol == "SECRETARIA":
        if path == "/":
            return True
        if path.startswith(("/jinetes", "/caballos", "/tropillas", "/inscripciones", "/acreditacion")):
            return True
        if path.startswith("/sorteos"):
            return metodo == "GET"
        if path.startswith("/resultados"):
            return metodo == "GET"
        return False

    if rol == "ACREDITACION":
        return path == "/" or path.startswith("/acreditacion")

    if rol in {"LOCUCION", "TV"}:
        if path == "/":
            return True
        if path.startswith(("/sorteos", "/resultados")):
            return metodo == "GET"
        return False

    return False
