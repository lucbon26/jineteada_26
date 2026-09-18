"""Reglas deportivas por campeonato/categoría, separadas de sanciones maestras.

La política es pura y parametrizable. No se infieren causas históricas.
Una carga incompleta nunca equivale a cero puntos.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from app.models.repechaje import RepechajeCategoria
from sqlalchemy import select
from app.models.categoria import Categoria
from app.models.fecha import Fecha
from app.models.jinete import Jinete
from app.models.jinete_campeonato import JineteCampeonato
from app.models.jinete_fecha import JineteFecha
from app.models.resultado import ResultadoCategoria
from app.models.sorteo import Sorteo


@dataclass(frozen=True)
class PoliticaClasificacion:
    minimo_directo: Decimal = Decimal('5')

    def resolver(self, total, puntos_repechaje=None):
        if total >= self.minimo_directo:
            return 'activo', 'puntos_f1_f2'
        if total <= 0:
            return 'descalificado', 'puntos_f1_f2'
        if puntos_repechaje is None:
            return 'repechaje', 'puntos_f1_f2'
        return ('activo' if puntos_repechaje > 0 else 'descalificado'), 'puntos_repechaje'


POLITICA = PoliticaClasificacion()
EXCEPCIONES_FECHA = {'suspendida', 'cancelada', 'reprogramada'}


def fechas_oficiales(db, campeonato_id):
    return db.scalars(select(Fecha).where(
        Fecha.campeonato_id == campeonato_id,
        Fecha.estado.not_in(EXCEPCIONES_FECHA),
    ).order_by(Fecha.fecha, Fecha.id)).all()


def puntos_carga(carga):
    if carga is None:
        return None
    oficiales = [d for d in carga.sorteo.detalles if not d.es_reserva and d.jinete_id is not None]
    filas = {r.sorteo_detalle_id: r for r in carga.detalles}
    if not oficiales or any(d.id not in filas or filas[d.id].puntos is None for d in oficiales):
        return None
    puntos = {}
    for d in oficiales:
        puntos[d.jinete_id] = puntos.get(d.jinete_id, Decimal('0')) + Decimal(filas[d.id].puntos)
    return puntos


def base_categoria(db, campeonato_id, categoria_id, solo_publicados=False):
    categoria = db.get(Categoria, categoria_id)
    if not categoria or not categoria.puntua_campeonato:
        return {}, ''
    fechas = fechas_oficiales(db, campeonato_id)[:2]
    if len(fechas) < 2:
        return None, ''
    permitidos = {'publicado'} if solo_publicados else {'finalizado', 'publicado'}
    puntos = []
    for fecha in fechas:
        carga = db.scalar(select(ResultadoCategoria).join(Sorteo).where(
            Sorteo.fecha_id == fecha.id, Sorteo.categoria_id == categoria_id,
            ResultadoCategoria.estado.in_(permitidos)))
        puntos.append(puntos_carga(carga))
    if puntos[0] is None or puntos[1] is None:
        return None, ''
    inscriptos = db.scalars(select(JineteCampeonato).where(
        JineteCampeonato.campeonato_id == campeonato_id,
        JineteCampeonato.categoria_id == categoria_id)).all()
    totales = {pre.jinete_id: puntos[0].get(pre.jinete_id, Decimal('0')) + puntos[1].get(pre.jinete_id, Decimal('0')) for pre in inscriptos}
    contenido = [categoria_id, [f.id for f in fechas], sorted((jid, str(total.quantize(Decimal('.01')))) for jid, total in totales.items())]
    firma = hashlib.sha256(json.dumps(contenido, separators=(',', ':')).encode()).hexdigest()
    return totales, firma


def candidatos_repechaje(totales):
    return {jid for jid, total in (totales or {}).items() if 0 < total < POLITICA.minimo_directo}


def puntos_repechaje_confirmados(db, campeonato_id, categoria_id, totales, solo_publicados=False):
    """Devuelve los puntos de F3 para quienes llegaron a repechaje.

    F3 ES el repechaje: no existe una planilla previa independiente. Mientras F3
    no tenga una carga completa/finalizada (o publicada para la web), devuelve
    None y esos jinetes conservan estado ``repechaje``.
    """
    fechas = fechas_oficiales(db, campeonato_id)
    if len(fechas) < 3:
        return None
    permitidos = {'publicado'} if solo_publicados else {'finalizado', 'publicado'}
    carga = db.scalar(select(ResultadoCategoria).join(Sorteo).where(
        Sorteo.fecha_id == fechas[2].id,
        Sorteo.categoria_id == categoria_id,
        ResultadoCategoria.estado.in_(permitidos),
    ))
    puntos = puntos_carga(carga)
    if puntos is None:
        return None
    return {jid: puntos.get(jid, Decimal('0')) for jid in candidatos_repechaje(totales)}


def evaluar_categoria(db, campeonato_id, categoria_id, solo_publicados=False):
    totales, firma = base_categoria(db, campeonato_id, categoria_id, solo_publicados)
    if totales is None:
        return {}
    puntos_f3 = puntos_repechaje_confirmados(db, campeonato_id, categoria_id, totales, solo_publicados)
    return {jid: POLITICA.resolver(total, None if puntos_f3 is None else puntos_f3.get(jid)) for jid, total in totales.items()}


def es_f3_o_posterior(db, fecha):
    fechas = fechas_oficiales(db, fecha.campeonato_id)
    return len(fechas) >= 3 and (fecha.fecha, fecha.id) >= (fechas[2].fecha, fechas[2].id)


def bloqueo_sorteo(db, fecha, categoria):
    if not categoria.puntua_campeonato or not es_f3_o_posterior(db, fecha):
        return None
    totales, firma = base_categoria(db, fecha.campeonato_id, categoria.id)
    if totales is None:
        return 'Primero completá y finalizá los resultados de F1 y F2 de esta categoría.'
    fechas = fechas_oficiales(db, fecha.campeonato_id)
    if len(fechas) >= 4 and fecha.id != fechas[2].id and puntos_repechaje_confirmados(db, fecha.campeonato_id, categoria.id, totales) is None:
        return 'Primero completá y finalizá los resultados de F3 (repechaje) antes de sortear una fecha posterior.'
    return None


def hay_sorteo_posterior(db, categoria):
    fechas = fechas_oficiales(db, categoria.campeonato_id)[2:]
    return bool(fechas) and db.scalar(select(Sorteo.id).where(Sorteo.categoria_id == categoria.id, Sorteo.fecha_id.in_([f.id for f in fechas])).limit(1)) is not None


def recalcular_categoria(db, campeonato_id, categoria_id):
    calculados = evaluar_categoria(db, campeonato_id, categoria_id)
    cambios = 0
    for pre in db.scalars(select(JineteCampeonato).where(
        JineteCampeonato.campeonato_id == campeonato_id,
        JineteCampeonato.categoria_id == categoria_id)).all():
        estado, causa = calculados.get(pre.jinete_id, (None, None))
        if (pre.estado_clasificacion, pre.causa_clasificacion, pre.categoria_clasificacion_id) != (estado, causa, categoria_id):
            pre.estado_clasificacion, pre.causa_clasificacion = estado, causa
            pre.categoria_clasificacion_id = categoria_id
            cambios += 1
    sincronizar_asistencia_f3(db, campeonato_id, categoria_id, calculados)
    return cambios


def bloqueo_maestro(jinete):
    """Estados administrativos/deportivos independientes que sí bloquean.

    ``historica_sin_causa`` y ``puntos_legacy`` son residuos de la regla vieja y
    no deben imponerse sobre la clasificación por campeonato/categoría.
    """
    if jinete is None:
        return True
    if jinete.estado == 'activo':
        return False
    if jinete.estado == 'descalificado' and jinete.estado_causa in {'historica_sin_causa', 'puntos_legacy'}:
        return False
    return True


def habilitado(db, jinete, fecha, categoria_id, *, para_sorteo=False):
    if bloqueo_maestro(jinete):
        return False
    categoria = db.get(Categoria, categoria_id)
    if categoria and not categoria.puntua_campeonato:
        return True
    estado = evaluar_categoria(db, fecha.campeonato_id, categoria_id).get(jinete.id, (None, None))[0]
    if estado == 'descalificado':
        return False
    if es_f3_o_posterior(db, fecha):
        fechas = fechas_oficiales(db, fecha.campeonato_id)
        if fecha.id == fechas[2].id:
            # F3 es el repechaje: entran directos (>=5) y repechaje (0<p<5).
            return estado in {'activo', 'repechaje'}
        # Desde F4 sólo siguen los directos y quienes obtuvieron >0 en F3.
        return estado == 'activo'
    return True


def sincronizar_asistencia_f3(db, campeonato_id, categoria_id, calculados):
    """Excluir eliminados de la asistencia habilitada, sin borrar su acreditación.

    El motivo conserva el estado previo para una corrección/reapertura anterior
    al sorteo. Ausencias y sanciones independientes no se modifican.
    """
    fechas = fechas_oficiales(db, campeonato_id)
    if len(fechas) < 3:
        return
    fecha = fechas[2]
    if db.scalar(select(Sorteo.id).where(Sorteo.fecha_id == fecha.id, Sorteo.categoria_id == categoria_id)) is not None:
        return
    prefijo = 'eliminado_repechaje:'
    filas = db.scalars(select(JineteFecha).where(JineteFecha.fecha_id == fecha.id, JineteFecha.categoria_id == categoria_id)).all()
    for fila in filas:
        estado, causa = calculados.get(fila.jinete_id, (None, None))
        if estado == 'descalificado' and causa == 'puntos_repechaje':
            if fila.estado in {'pendiente', 'validado'}:
                fila.motivo_no_habilitado = prefijo + fila.estado
                fila.estado = 'no_habilitado'
        elif estado in {'activo', 'repechaje'} and fila.estado == 'no_habilitado' and (fila.motivo_no_habilitado or '').startswith(prefijo):
            previo = fila.motivo_no_habilitado[len(prefijo):]
            jinete = db.get(Jinete, fila.jinete_id)
            if previo in {'pendiente', 'validado'} and jinete and jinete.estado == 'activo':
                fila.estado = previo
                fila.motivo_no_habilitado = None


def estados_publicos(db, campeonato_id, categoria_id):
    calculados = evaluar_categoria(db, campeonato_id, categoria_id, solo_publicados=True)
    etiquetas = {'activo': 'CLASIFICADO', 'repechaje': 'REPECHAJE', 'descalificado': 'DESCALIFICADO'}
    salida = {}
    for pre in db.scalars(select(JineteCampeonato).where(
        JineteCampeonato.campeonato_id == campeonato_id,
        JineteCampeonato.categoria_id == categoria_id)).all():
        jinete = pre.jinete
        if bloqueo_maestro(jinete):
            salida[jinete.id] = jinete.estado.upper()
        else:
            salida[jinete.id] = etiquetas.get(calculados.get(jinete.id, (None, None))[0], 'EN COMPETENCIA')
    return salida


def ausencias_consecutivas(db, jinete_id, campeonato_id, hasta_fecha=None):
    fechas = fechas_oficiales(db, campeonato_id)
    if hasta_fecha is not None:
        fechas = [f for f in fechas if (f.fecha, f.id) <= (hasta_fecha.fecha, hasta_fecha.id)]
    participaciones = {p.fecha_id: p.estado for p in db.scalars(select(JineteFecha).join(Fecha).where(
        JineteFecha.jinete_id == jinete_id, Fecha.campeonato_id == campeonato_id)).all()}
    racha = 0
    for fecha in fechas:
        if not fecha.inscripcion_cerrada and (hasta_fecha is None or fecha.id != hasta_fecha.id):
            racha = 0
            continue
        racha = racha + 1 if participaciones.get(fecha.id) == 'ausente' else 0
    return racha
