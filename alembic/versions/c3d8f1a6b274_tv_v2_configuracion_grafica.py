"""tv v2 configuracion grafica

Revision ID: c3d8f1a6b274
Revises: a81e4c7d2f90
Create Date: 2026-09-08
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c3d8f1a6b274"
down_revision: Union[str, None] = "a81e4c7d2f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columnas = [
        ("graph_color_principal", sa.String(20), "#00A651"),
        ("graph_color_fondo", sa.String(20), "#101820"),
        ("graph_color_texto", sa.String(20), "#FFFFFF"),
        ("graph_color_secundario", sa.String(20), "#D9E2E8"),
        ("graph_nombre_px", sa.Integer(), "54"),
        ("graph_detalle_px", sa.Integer(), "31"),
        ("graph_ancho_px", sa.Integer(), "1280"),
        ("graph_left_px", sa.Integer(), "64"),
        ("graph_bottom_px", sa.Integer(), "72"),
        ("ticker_color_fondo", sa.String(20), "#101820"),
        ("ticker_color_texto", sa.String(20), "#FFFFFF"),
        ("ticker_color_acento", sa.String(20), "#00A651"),
        ("ticker_fuente_px", sa.Integer(), "30"),
        ("ticker_alto_px", sa.Integer(), "96"),
        ("ticker_bottom_px", sa.Integer(), "48"),
        ("ticker_velocidad_seg", sa.Integer(), "28"),
        ("tabla_color_fondo", sa.String(20), "#101820"),
        ("tabla_color_texto", sa.String(20), "#FFFFFF"),
        ("tabla_color_acento", sa.String(20), "#00A651"),
        ("tabla_fuente_px", sa.Integer(), "30"),
        ("tabla_filas", sa.Integer(), "8"),
        ("tabla_rotacion_seg", sa.Integer(), "8"),
    ]
    for nombre, tipo, defecto in columnas:
        op.add_column("tv_salidas", sa.Column(nombre, tipo, nullable=False, server_default=defecto))


def downgrade() -> None:
    for nombre in reversed([
        "graph_color_principal","graph_color_fondo","graph_color_texto","graph_color_secundario",
        "graph_nombre_px","graph_detalle_px","graph_ancho_px","graph_left_px","graph_bottom_px",
        "ticker_color_fondo","ticker_color_texto","ticker_color_acento","ticker_fuente_px","ticker_alto_px","ticker_bottom_px","ticker_velocidad_seg",
        "tabla_color_fondo","tabla_color_texto","tabla_color_acento","tabla_fuente_px","tabla_filas","tabla_rotacion_seg",
    ]):
        op.drop_column("tv_salidas", nombre)
