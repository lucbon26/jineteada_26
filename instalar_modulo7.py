from pathlib import Path
import re

PROJECT = Path.cwd()
if not (PROJECT / "app" / "main.py").exists():
    raise SystemExit("Ejecutá este instalador desde C:\\jineteada_26")


def integrar_main():
    p = PROJECT / "app" / "main.py"
    txt = p.read_text(encoding="utf-8")

    if "# MODULO7_INSCRIPCIONES" not in txt:
        txt += """
# MODULO7_INSCRIPCIONES
from app.routers import inscripciones as inscripciones_router
app.include_router(inscripciones_router.router)
"""
        print("OK: Inscripciones integrado")

    if "# MODULO7_ACREDITACION" not in txt:
        txt += """
# MODULO7_ACREDITACION
from app.routers import acreditacion as acreditacion_router
app.include_router(acreditacion_router.router)

import unicodedata as _ud_mod7
from fastapi.responses import RedirectResponse as _RR_mod7

def _rol_mod7(valor):
    texto = (valor or "").strip().lower()
    return "".join(c for c in _ud_mod7.normalize("NFD", texto) if _ud_mod7.category(c) != "Mn")

@app.middleware("http")
async def _solo_acreditacion_mod7(request, call_next):
    if _rol_mod7(request.session.get("usuario_rol")) == "acreditacion":
        path = request.url.path
        permitido = (
            path.startswith("/acreditacion")
            or path.startswith("/static")
            or path == "/login"
            or path.startswith("/logout")
            or path.startswith("/favicon")
        )
        if not permitido:
            return _RR_mod7(url="/acreditacion", status_code=303)
    return await call_next(request)
"""
        print("OK: Acreditación móvil y restricción de rol integradas")

    p.write_text(txt, encoding="utf-8")


def dependencia_qr():
    p = PROJECT / "requirements.txt"
    if not p.exists():
        return
    txt = p.read_text(encoding="utf-8")
    if "qrcode" not in txt.lower():
        with p.open("a", encoding="utf-8") as f:
            if txt and not txt.endswith("\n"):
                f.write("\n")
            f.write("qrcode[pil]>=7.4\n")
        print("OK: qrcode[pil] agregado")


def acceso_fecha():
    p = PROJECT / "app" / "templates" / "fechas" / "detalle.html"
    if not p.exists():
        print("AVISO: no encontré fechas/detalle.html")
        return
    html = p.read_text(encoding="utf-8")
    if "/inscripciones/fecha/" in html:
        return

    variable = None
    if re.search(r"\{\{\s*fecha_evento\.", html):
        variable = "fecha_evento"
    elif re.search(r"\{\{\s*fecha\.", html):
        variable = "fecha"

    if not variable:
        print("AVISO: no detecté variable de fecha; usá /inscripciones")
        return

    bloque = """
<div class="card shadow-sm mt-4">
  <div class="card-body d-flex justify-content-between align-items-center">
    <div><h4 class="mb-1">📝 Inscripciones</h4><div class="text-muted">Validación QR y habilitación para sorteo.</div></div>
    <a href="/inscripciones/fecha/{{ VAR.id }}" class="btn btn-primary">Abrir inscripciones</a>
  </div>
</div>
""".replace("VAR", variable)

    pos = html.rfind("{% endblock %}")
    if pos != -1:
        html = html[:pos] + bloque + html[pos:]
        p.write_text(html, encoding="utf-8")
        print("OK: acceso desde detalle de Fecha agregado")


def rol_template():
    cambiados = 0
    for p in (PROJECT / "app" / "templates").rglob("*.html"):
        html = p.read_text(encoding="utf-8", errors="ignore")
        if "Acreditación" in html or "Acreditacion" in html:
            continue
        if "<option" not in html:
            continue
        m = re.search(r'(<option[^>]*value=["\']Locución["\'][^>]*>.*?</option>)', html, re.I | re.S)
        if not m:
            m = re.search(r'(<option[^>]*value=["\']Locucion["\'][^>]*>.*?</option>)', html, re.I | re.S)
        if m:
            html = html[:m.end()] + '\n<option value="Acreditación">Acreditación</option>' + html[m.end():]
            p.write_text(html, encoding="utf-8")
            cambiados += 1
    if cambiados:
        print(f"OK: rol Acreditación agregado en {cambiados} selector(es)")
    else:
        print("AVISO: no encontré selector de roles. El backend igualmente reconoce 'Acreditación'.")


integrar_main()
dependencia_qr()
acceso_fecha()
rol_template()

print("\nMódulo 7 completo integrado.")
print("Ejecutá:")
print("  pip install -r requirements.txt")
print("  alembic upgrade head")
print("  uvicorn app.main:app --reload --host 0.0.0.0")
print("\nAdministración: http://127.0.0.1:8000/inscripciones")
print("Celular: http://IP-DE-LA-PC:8000/acreditacion")
