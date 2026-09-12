"""Modulo Resultados: carga por sorteo oficial y publicacion

Revision ID: f6b1c92e4d70
Revises: e7a91c5d2b40
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6b1c92e4d70"
down_revision: Union[str, Sequence[str], None] = "e7a91c5d2b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resultados_categorias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sorteo_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.Column("finalizado_en", sa.DateTime(), nullable=True),
        sa.Column("publicado_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sorteo_id"], ["sorteos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sorteo_id"),
    )
    op.create_index(op.f("ix_resultados_categorias_id"), "resultados_categorias", ["id"], unique=False)
    op.create_index(op.f("ix_resultados_categorias_sorteo_id"), "resultados_categorias", ["sorteo_id"], unique=True)
    op.create_index(op.f("ix_resultados_categorias_estado"), "resultados_categorias", ["estado"], unique=False)

    op.create_table(
        "resultados_detalles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resultado_categoria_id", sa.Integer(), nullable=False),
        sa.Column("sorteo_detalle_id", sa.Integer(), nullable=False),
        sa.Column("puntos", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["resultado_categoria_id"], ["resultados_categorias.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sorteo_detalle_id"], ["sorteo_detalles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resultado_categoria_id", "sorteo_detalle_id", name="uq_resultado_categoria_detalle"),
    )
    op.create_index(op.f("ix_resultados_detalles_id"), "resultados_detalles", ["id"], unique=False)
    op.create_index(op.f("ix_resultados_detalles_resultado_categoria_id"), "resultados_detalles", ["resultado_categoria_id"], unique=False)
    op.create_index(op.f("ix_resultados_detalles_sorteo_detalle_id"), "resultados_detalles", ["sorteo_detalle_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_resultados_detalles_sorteo_detalle_id"), table_name="resultados_detalles")
    op.drop_index(op.f("ix_resultados_detalles_resultado_categoria_id"), table_name="resultados_detalles")
    op.drop_index(op.f("ix_resultados_detalles_id"), table_name="resultados_detalles")
    op.drop_table("resultados_detalles")
    op.drop_index(op.f("ix_resultados_categorias_estado"), table_name="resultados_categorias")
    op.drop_index(op.f("ix_resultados_categorias_sorteo_id"), table_name="resultados_categorias")
    op.drop_index(op.f("ix_resultados_categorias_id"), table_name="resultados_categorias")
    op.drop_table("resultados_categorias")
