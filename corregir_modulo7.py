from pathlib import Path
import re

main_path = Path("app/main.py")
if not main_path.exists():
    raise SystemExit("Ejecutá este script desde C:\\jineteada_26")

texto = main_path.read_text(encoding="utf-8")

inicio = texto.find("# MODULO7_ACREDITACION")
if inicio != -1:
    bloque = texto[inicio:]
    include = ""
    m = re.search(
        r"from app\.routers import acreditacion as acreditacion_router\s*"
        r"app\.include_router\(acreditacion_router\.router\)",
        bloque,
    )
    if m:
        include = (
            "\n# MODULO7_ACREDITACION\n"
            "from app.routers import acreditacion as acreditacion_router\n"
            "app.include_router(acreditacion_router.router)\n"
        )

    texto = texto[:inicio].rstrip() + "\n" + include

guardia = '''
# MODULO7_GUARDIA_ACREDITACION
import unicodedata as _unicodedata_mod7
from fastapi.responses import RedirectResponse as _RedirectResponse_mod7

def _rol_mod7(valor):
    texto_rol = (valor or "").strip().lower()
    return "".join(
        c for c in _unicodedata_mod7.normalize("NFD", texto_rol)
        if _unicodedata_mod7.category(c) != "Mn"
    )

@app.middleware("http")
async def _solo_acreditacion_mod7(request, call_next):
    rol = _rol_mod7(request.session.get("usuario_rol"))

    if rol == "acreditacion":
        path = request.url.path
        permitido = (
            path.startswith("/acreditacion")
            or path.startswith("/static")
            or path == "/login"
            or path.startswith("/logout")
            or path.startswith("/favicon")
        )
        if not permitido:
            return _RedirectResponse_mod7(
                url="/acreditacion",
                status_code=303,
            )

    return await call_next(request)

'''

if "# MODULO7_GUARDIA_ACREDITACION" not in texto:
    patron = re.compile(
        r"^app\.add_middleware\(\s*SessionMiddleware\b",
        re.MULTILINE,
    )
    m = patron.search(texto)

    if not m:
        raise SystemExit(
            "No encontré app.add_middleware(SessionMiddleware...) en app/main.py. "
            "No se modificó el archivo."
        )

    texto = texto[:m.start()] + guardia + texto[m.start():]

main_path.write_text(texto, encoding="utf-8")

print("OK: corregido el orden del middleware de Acreditación.")
print()
print("Ahora ejecutá:")
print("  alembic current")
print("  alembic upgrade head")
print("  alembic current")
print()
print("Después:")
print("  uvicorn app.main:app --reload --host 0.0.0.0")
