"""Recalcula clasificación y repara estados históricos de forma conservadora.

Por defecto sólo simula. ``--aplicar`` persiste cambios. Una descalificación
con causa explícita (ausencias, suspensión, manual, etc.) nunca se levanta.
Los registros ``historica_sin_causa`` sólo se reactivan cuando la clasificación
actual da ACTIVO o REPECHAJE y no existe evidencia independiente de sanción.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.core.database import SessionLocal
import app.models
from app.models.jinete import Jinete
from app.models.jinete_fecha import JineteFecha
from app.models.categoria import Categoria
from app.services.clasificacion import evaluar_categoria, recalcular_categoria, fechas_oficiales

CAUSAS_REPARABLES = {"historica_sin_causa", "puntos_legacy"}
MOTIVOS_SANCION = {"suspendido", "sancion", "manual", "inactivo"}


def evidencia_sancion_independiente(db, jinete):
    """Devuelve evidencias que impiden levantar el estado maestro."""
    evidencias = []
    participaciones = db.scalars(select(JineteFecha).where(JineteFecha.jinete_id == jinete.id)).all()
    campeonatos = {p.fecha.campeonato_id for p in participaciones if p.fecha is not None}
    estados_por_fecha = {p.fecha_id: p.estado for p in participaciones}
    for campeonato_id in sorted(campeonatos):
        racha = 0
        max_racha = 0
        for fecha in fechas_oficiales(db, campeonato_id):
            if not fecha.inscripcion_cerrada:
                racha = 0
                continue
            racha = racha + 1 if estados_por_fecha.get(fecha.id) == "ausente" else 0
            max_racha = max(max_racha, racha)
        if max_racha >= 2:
            evidencias.append(f"2_ausencias_consecutivas:campeonato_{campeonato_id}")
    for p in participaciones:
        motivo = (p.motivo_no_habilitado or "").strip().lower()
        if motivo in MOTIVOS_SANCION:
            evidencias.append(f"{motivo}:fecha_{p.fecha_id}")
    return sorted(set(evidencias))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    # Compatibilidad: permite revisar una causa NULL puntual, pero jamás salta protecciones.
    parser.add_argument("--confirmar-origen-puntos", type=int, nargs="*", default=[], metavar="ID")
    args = parser.parse_args()
    reporte = {
        "modo": "aplicar" if args.aplicar else "simulacion",
        "categorias": [],
        "reparados": [],
        "conservados": [],
        "revision_manual": [],
    }
    with SessionLocal() as db:
        # Primero guardar/recalcular el estado deportivo por campeonato y categoría.
        for cat in db.scalars(select(Categoria)).all():
            calculados = evaluar_categoria(db, cat.campeonato_id, cat.id)
            reporte["categorias"].append({"id": cat.id, "estados": calculados})
            recalcular_categoria(db, cat.campeonato_id, cat.id)

        for jinete in db.scalars(select(Jinete).where(Jinete.estado == "descalificado")).all():
            causa = jinete.estado_causa
            reparable = causa in CAUSAS_REPARABLES or (causa is None and jinete.id in args.confirmar_origen_puntos)
            candidatas = [
                pre for pre in jinete.campeonatos
                if pre.estado_clasificacion in {"activo", "repechaje"}
            ]
            evidencias = evidencia_sancion_independiente(db, jinete)

            if reparable and candidatas and not evidencias:
                anterior = jinete.estado
                jinete.estado = "activo"
                jinete.estado_causa = "correccion_historica_clasificacion"
                reporte["reparados"].append({
                    "id": jinete.id,
                    "nombre": jinete.nombre_completo,
                    "estado_anterior": anterior,
                    "causa_anterior": causa,
                    "categorias": [
                        {"categoria_id": pre.categoria_id, "estado": pre.estado_clasificacion, "causa": pre.causa_clasificacion}
                        for pre in candidatas
                    ],
                })
            elif causa not in CAUSAS_REPARABLES and causa is not None:
                reporte["conservados"].append({"id": jinete.id, "causa": causa})
            elif reparable and evidencias:
                reporte["revision_manual"].append({
                    "id": jinete.id, "nombre": jinete.nombre_completo,
                    "causa": causa, "evidencia_sancion": evidencias,
                    "estados_calculados": [
                        {"categoria_id": pre.categoria_id, "estado": pre.estado_clasificacion}
                        for pre in candidatas
                    ],
                })
            elif reparable and not candidatas:
                # Cero puntos / base incompleta / descalificación deportiva vigente: no reactivar.
                reporte["conservados"].append({"id": jinete.id, "causa": causa, "motivo": "sin_estado_activo_o_repechaje"})

        if args.aplicar:
            db.commit()
        else:
            db.rollback()
    print(json.dumps(reporte, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
