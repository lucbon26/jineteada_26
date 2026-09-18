"""Vista previa por defecto. --aplicar guarda; causas desconocidas requieren revisión."""
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
from app.services.clasificacion import evaluar_categoria, recalcular_categoria, fechas_oficiales, puntos_carga
from app.models.resultado import ResultadoCategoria
from app.models.sorteo import Sorteo


def afectado_por_regla_anterior(db, pre):
    fechas = fechas_oficiales(db, pre.campeonato_id)[:2]
    if len(fechas) != 2:
        return False
    total = 0
    for fecha in fechas:
        carga = db.scalar(select(ResultadoCategoria).join(Sorteo).where(
            Sorteo.fecha_id == fecha.id, Sorteo.categoria_id == pre.categoria_id,
            ResultadoCategoria.estado.in_(['finalizado', 'publicado'])))
        puntos = puntos_carga(carga)
        if puntos is None:
            return False
        total += puntos.get(pre.jinete_id, 0)
    # La regla vieja podía haber dejado descalificado tanto a quien hoy es
    # repechaje (0<total<5) como a quien hoy debe estar activo (total>=5).
    return total > 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    parser.add_argument('--confirmar-origen-puntos', type=int, nargs='*', default=[], metavar='ID')
    args = parser.parse_args()
    reporte = {'modo': 'aplicar' if args.aplicar else 'simulacion', 'categorias': [], 'revision_manual': [], 'reactivados': []}
    with SessionLocal() as db:
        for cat in db.scalars(select(Categoria)).all():
            calculados = evaluar_categoria(db, cat.campeonato_id, cat.id)
            reporte['categorias'].append({'id': cat.id, 'estados': calculados})
            recalcular_categoria(db, cat.campeonato_id, cat.id)
        for jinete in db.scalars(select(Jinete).where(Jinete.estado == 'descalificado')).all():
            origen_confirmado = jinete.estado_causa in {'puntos_legacy', 'historica_sin_causa'} or (
                jinete.id in args.confirmar_origen_puntos and jinete.estado_causa is None)
            # Proteger sanciones independientes. Dos ausencias sólo descalifican si
            # fueron consecutivas dentro del mismo campeonato.
            participaciones = db.scalars(select(JineteFecha).where(JineteFecha.jinete_id == jinete.id)).all()
            sancion = any((p.motivo_no_habilitado or '') in {'suspendido', 'sancion', 'manual', 'limite_suspensiones'} for p in participaciones)
            for pre in jinete.campeonatos:
                fechas = fechas_oficiales(db, pre.campeonato_id)
                estados = {p.fecha_id: p.estado for p in participaciones if p.categoria_id == pre.categoria_id}
                if any(estados.get(fechas[i - 1].id) == 'ausente' and estados.get(fechas[i].id) == 'ausente' for i in range(1, len(fechas))):
                    sancion = True
                    break
            candidatas = [pre for pre in jinete.campeonatos if pre.estado_clasificacion in {'activo', 'repechaje'} and afectado_por_regla_anterior(db, pre)]
            if origen_confirmado and not sancion and candidatas:
                jinete.estado = 'activo'
                jinete.estado_causa = 'correccion_puntos_legacy'
                reporte['reactivados'].append(jinete.id)
            else:
                reporte['revision_manual'].append({
                    'id': jinete.id, 'nombre': jinete.nombre_completo,
                    'causa': jinete.estado_causa, 'evidencia_sancion': sancion,
                    'candidato_vieja_regla_puntos': bool(candidatas),
                    'categorias_afectadas': [pre.categoria_id for pre in candidatas],
                })
        if args.aplicar:
            db.commit()
        else:
            db.rollback()
    print(json.dumps(reporte, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
