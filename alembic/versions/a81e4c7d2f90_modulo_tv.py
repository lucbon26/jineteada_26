"""modulo tv

Revision ID: a81e4c7d2f90
Revises: b63f1a4d8c22
Create Date: 2026-09-08
"""

from typing import Sequence, Union
import secrets

from alembic import op
import sqlalchemy as sa

revision: str = "a81e4c7d2f90"
down_revision: Union[str, None] = "b63f1a4d8c22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tv_salidas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=80), nullable=False),
        sa.Column("escena", sa.String(length=30), nullable=False, server_default="oculto"),
        sa.Column("sorteo_id", sa.Integer(), nullable=True),
        sa.Column("detalle_id", sa.Integer(), nullable=True),
        sa.Column("tabla_pagina", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tabla_auto", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ticker_cantidad", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["detalle_id"], ["sorteo_detalles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sorteo_id"], ["sorteos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_tv_salidas_token"),
    )
    op.create_index("ix_tv_salidas_token", "tv_salidas", ["token"], unique=True)
    op.create_index("ix_tv_salidas_sorteo_id", "tv_salidas", ["sorteo_id"], unique=False)
    op.create_index("ix_tv_salidas_detalle_id", "tv_salidas", ["detalle_id"], unique=False)

    # Se crea una única salida principal. El operador puede regenerar el token
    # desde el panel y la URL anterior queda inmediatamente invalidada.
    op.execute(
        sa.text(
            "INSERT INTO tv_salidas "
            "(id, token, escena, tabla_pagina, tabla_auto, ticker_cantidad, actualizado_en) "
            "VALUES (1, :token, 'oculto', 1, :tabla_auto, 6, CURRENT_TIMESTAMP)"
        ).bindparams(token=secrets.token_urlsafe(32), tabla_auto=True)
    )


def downgrade() -> None:
    op.drop_index("ix_tv_salidas_detalle_id", table_name="tv_salidas")
    op.drop_index("ix_tv_salidas_sorteo_id", table_name="tv_salidas")
    op.drop_index("ix_tv_salidas_token", table_name="tv_salidas")
    op.drop_table("tv_salidas")
