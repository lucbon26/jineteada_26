"""Borrado explícito de dependencias; funciona también con FK activas en SQLite."""
from fastapi import HTTPException
from sqlalchemy import select, delete, update
from app.core.permissions import normalizar_rol
from app.models.campeonato import Campeonato
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.sorteo import Sorteo, SorteoDetalle
from app.models.sorteo_auditoria import SorteoAuditoria
from app.models.resultado import ResultadoCategoria, ResultadoDetalle
from app.models.jinete_fecha import JineteFecha
from app.models.jinete_campeonato import JineteCampeonato
from app.models.caballo_fecha import CaballoFecha
from app.models.caballo_historial import CaballoHistorial
from app.models.repechaje import RepechajeCategoria
from app.models.tv_salida import TvSalida
from app.services.clasificacion import recalcular_categoria


def exigir_borrado(request):
    if not request.session.get('usuario_id') or normalizar_rol(request.session.get('usuario_rol')) not in {'ADMIN', 'MASTER'}:
        raise HTTPException(403, 'Sólo ADMIN y MASTER pueden eliminar campeonatos, fechas o sorteos.')


def borrar_sorteos(db, ids):
    if not ids:
        return
    db.flush()
    detalles = select(SorteoDetalle.id).where(SorteoDetalle.sorteo_id.in_(ids))
    cargas = select(ResultadoCategoria.id).where(ResultadoCategoria.sorteo_id.in_(ids))
    # Las imágenes congeladas de TV y sus URLs permanecen; quitar sólo referencias.
    db.execute(update(TvSalida).where(TvSalida.detalle_id.in_(detalles)).values(detalle_id=None))
    for nombre in ['sorteo_id', 'graph_sorteo_id', 'ticker_sorteo_id', 'tabla_sorteo_id', 'campeonato_sorteo_id']:
        db.execute(update(TvSalida).where(getattr(TvSalida, nombre).in_(ids)).values({nombre: None}))
    db.execute(delete(ResultadoDetalle).where(ResultadoDetalle.resultado_categoria_id.in_(cargas)))
    db.execute(delete(ResultadoCategoria).where(ResultadoCategoria.sorteo_id.in_(ids)))
    db.execute(delete(SorteoDetalle).where(SorteoDetalle.sorteo_id.in_(ids)))
    db.execute(delete(Sorteo).where(Sorteo.id.in_(ids)))


def borrar_fechas(db, ids):
    if not ids:
        return
    borrar_sorteos(db, list(db.scalars(select(Sorteo.id).where(Sorteo.fecha_id.in_(ids)))))
    db.execute(delete(SorteoAuditoria).where(SorteoAuditoria.fecha_id.in_(ids)))
    db.execute(delete(JineteFecha).where(JineteFecha.fecha_id.in_(ids)))
    db.execute(delete(CaballoFecha).where(CaballoFecha.fecha_id.in_(ids)))
    db.execute(update(CaballoHistorial).where(CaballoHistorial.fecha_id.in_(ids)).values(fecha_id=None))
    db.execute(delete(Fecha).where(Fecha.id.in_(ids)))


def borrar_campeonato(db, campeonato_id):
    borrar_fechas(db, list(db.scalars(select(Fecha.id).where(Fecha.campeonato_id == campeonato_id))))
    categorias = list(db.scalars(select(Categoria.id).where(Categoria.campeonato_id == campeonato_id)))
    db.execute(update(CaballoHistorial).where(CaballoHistorial.campeonato_id == campeonato_id).values(campeonato_id=None))
    db.execute(update(CaballoHistorial).where(CaballoHistorial.categoria_id.in_(categorias)).values(categoria_id=None))
    db.execute(delete(JineteCampeonato).where(JineteCampeonato.campeonato_id == campeonato_id))
    db.execute(delete(RepechajeCategoria).where(RepechajeCategoria.categoria_id.in_(categorias)))
    db.execute(delete(Categoria).where(Categoria.campeonato_id == campeonato_id))
    db.execute(delete(Campeonato).where(Campeonato.id == campeonato_id))


def recalcular_campeonato(db, campeonato_id):
    db.flush()
    for cid in db.scalars(select(Categoria.id).where(Categoria.campeonato_id == campeonato_id)).all():
        recalcular_categoria(db, campeonato_id, cid)
