from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fecha import Fecha
from app.models.resultado import ResultadoCategoria
from app.models.sorteo import Sorteo


def posiciones_campeonato(
    db: Session,
    campeonato_id: int,
    categoria_id: int,
    *,
    solo_publicados: bool = False,
) -> list[dict]:
    """Calcula la tabla acumulada por suma de puntos sin alterar datos oficiales."""
    estados = ["publicado"] if solo_publicados else ["finalizado", "publicado"]

    cargas = db.scalars(
        select(ResultadoCategoria)
        .join(Sorteo, Sorteo.id == ResultadoCategoria.sorteo_id)
        .join(Fecha, Fecha.id == Sorteo.fecha_id)
        .where(
            Fecha.campeonato_id == campeonato_id,
            Sorteo.categoria_id == categoria_id,
            ResultadoCategoria.estado.in_(estados),
        )
        .order_by(Fecha.fecha.asc(), Fecha.id.asc())
    ).all()

    acumulado: dict[int, dict] = {}
    for carga in cargas:
        for resultado in carga.detalles:
            detalle = resultado.sorteo_detalle
            if detalle is None or detalle.es_reserva or detalle.jinete_id is None:
                continue
            if resultado.puntos is None:
                continue

            fila = acumulado.setdefault(
                detalle.jinete_id,
                {
                    "jinete_id": detalle.jinete_id,
                    "jinete": detalle.jinete_nombre or "-",
                    "localidad": detalle.jinete_localidad or "-",
                    "puntos": Decimal("0"),
                    "fechas_puntuadas": 0,
                },
            )
            fila["puntos"] += Decimal(resultado.puntos)
            fila["fechas_puntuadas"] += 1

    ordenadas = sorted(
        acumulado.values(),
        key=lambda x: (-x["puntos"], str(x["jinete"]).upper()),
    )

    # Puestos únicos y consecutivos. En empate de puntaje se usa el orden
    # alfabético, sin compartir posición.
    for indice, fila in enumerate(ordenadas, start=1):
        fila["posicion"] = indice
        fila["puntos"] = float(fila["puntos"])

    return ordenadas
