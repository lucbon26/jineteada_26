"""Agregar transmisión YouTube a fechas

Revision ID: b63f1a4d8c22
Revises: f2c7a91d4e30
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b63f1a4d8c22"
down_revision: Union[str, None] = "f2c7a91d4e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columnas_fechas() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {columna["name"] for columna in inspector.get_columns("fechas")}


def upgrade() -> None:
    columnas = _columnas_fechas()

    # La migración es deliberadamente idempotente porque SQLite usa DDL
    # no transaccional: si una ejecución anterior falló luego de crear
    # alguna columna, puede volver a ejecutarse sin duplicarla.
    if "youtube_url" not in columnas:
        op.add_column(
            "fechas",
            sa.Column(
                "youtube_url",
                sa.String(length=500),
                nullable=True,
            ),
        )

    if "youtube_publicar" not in columnas:
        op.add_column(
            "fechas",
            sa.Column(
                "youtube_publicar",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # No intentamos DROP DEFAULT con ALTER COLUMN:
    # SQLite no soporta esa sintaxis. El default en DB es inocuo y además
    # garantiza False para registros creados fuera de SQLAlchemy.


def downgrade() -> None:
    columnas = _columnas_fechas()

    # batch_alter_table es portable para SQLite.
    with op.batch_alter_table("fechas") as batch_op:
        if "youtube_publicar" in columnas:
            batch_op.drop_column("youtube_publicar")
        if "youtube_url" in columnas:
            batch_op.drop_column("youtube_url")
