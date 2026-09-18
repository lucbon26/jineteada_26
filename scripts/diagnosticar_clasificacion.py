"""Diagnóstico de sólo lectura; no recalcula ni modifica estados."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from sqlalchemy import inspect, select, text
from app.core.database import SessionLocal
import app.models
from app.models.categoria import Categoria
from app.models.campeonato import Campeonato
from app.models.fecha import Fecha
from app.models.jinete_fecha import JineteFecha
from app.models.jinete_campeonato import JineteCampeonato
from app.models.resultado import ResultadoCategoria
from app.models.repechaje import RepechajeCategoria
from app.models.sorteo import Sorteo
from app.services.clasificacion import (
    base_categoria, evaluar_categoria, estados_publicos, fechas_oficiales,
    puntos_carga, puntos_repechaje_confirmados,
)


def informe(db, campeonato_id=None):
    salida = {'solo_lectura': True, 'categorias': []}
    consulta = select(Categoria).order_by(Categoria.campeonato_id, Categoria.id)
    if campeonato_id is not None:
        consulta = consulta.where(Categoria.campeonato_id == campeonato_id)
    for cat in db.scalars(consulta).all():
        camp = db.get(Campeonato, cat.campeonato_id)
        totales, firma = base_categoria(db, camp.id, cat.id)
        publicos, _ = base_categoria(db, camp.id, cat.id, solo_publicados=True)
        calculados = evaluar_categoria(db, camp.id, cat.id)
        etiquetas = estados_publicos(db, camp.id, cat.id)
        planilla = db.get(RepechajeCategoria, cat.id)
        item = {
            'campeonato_id': camp.id, 'campeonato': camp.nombre,
            'categoria_id': cat.id, 'categoria': cat.nombre,
            'puntua_campeonato': cat.puntua_campeonato,
            'base_interna_completa': totales is not None,
            'base_publica_completa': publicos is not None,
            'fechas_tomadas_como_f1_f2': [],
            'repechaje': None if planilla is None else {
                'estado': planilla.estado, 'confirmado_en': str(planilla.confirmado_en),
                'firma_vigente': planilla.base_firma == firma,
                'puntos_confirmados': None if totales is None else puntos_repechaje_confirmados(db, cat.id, totales, firma),
            },
            'jinetes': [],
        }
        for fecha in fechas_oficiales(db, camp.id)[:2]:
            cargas = db.scalars(select(ResultadoCategoria).join(Sorteo).where(
                Sorteo.fecha_id == fecha.id, Sorteo.categoria_id == cat.id)).all()
            item['fechas_tomadas_como_f1_f2'].append({
                'id': fecha.id, 'nombre': fecha.nombre, 'dia': str(fecha.fecha),
                'estado': fecha.estado, 'inscripcion_cerrada': fecha.inscripcion_cerrada,
                'cargas': [{'id': c.id, 'estado': c.estado, 'puntos_completos': puntos_carga(c) is not None} for c in cargas],
            })
        for pre in db.scalars(select(JineteCampeonato).where(
            JineteCampeonato.campeonato_id == camp.id, JineteCampeonato.categoria_id == cat.id)).all():
            j = pre.jinete
            asistencia = db.execute(select(JineteFecha, Fecha).join(Fecha).where(
                JineteFecha.jinete_id == j.id).order_by(Fecha.fecha, Fecha.id)).all()
            item['jinetes'].append({
                'id': j.id, 'nombre': j.nombre_completo,
                'estado_padron': j.estado, 'causa_padron': j.estado_causa,
                'clasificacion_guardada': pre.estado_clasificacion,
                'causa_guardada': pre.causa_clasificacion,
                'puntos_f1_f2': None if totales is None else totales.get(j.id),
                'calculo_actual': calculados.get(j.id), 'etiqueta_publica': etiquetas.get(j.id),
                'asistencia': [{'campeonato_id': f.campeonato_id, 'fecha_id': f.id,
                    'fecha': f.nombre, 'categoria_id': p.categoria_id,
                    'estado': p.estado, 'motivo': p.motivo_no_habilitado}
                    for p, f in asistencia],
            })
        salida['categorias'].append(item)
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campeonato', type=int)
    args = parser.parse_args()
    with SessionLocal() as db:
        # Impedir escrituras accidentales, también si cambian los servicios importados.
        dialecto = db.get_bind().dialect.name
        if dialecto == 'postgresql':
            db.execute(text('SET TRANSACTION READ ONLY'))
        elif dialecto == 'sqlite':
            db.execute(text('PRAGMA query_only = ON'))
        with db.no_autoflush:
            datos = informe(db, args.campeonato)
            datos['alembic'] = list(db.scalars(text('SELECT version_num FROM alembic_version'))) if inspect(db.get_bind()).has_table('alembic_version') else []
            datos['archivos_sha256'] = {nombre: hashlib.sha256((RAIZ / nombre).read_bytes()).hexdigest()
                for nombre in ['app/services/clasificacion.py', 'app/services/resultados.py', 'app/routers/inscripciones.py']}
        db.rollback()
    print(json.dumps(datos, ensure_ascii=True, indent=2, default=str))


if __name__ == '__main__':
    main()
