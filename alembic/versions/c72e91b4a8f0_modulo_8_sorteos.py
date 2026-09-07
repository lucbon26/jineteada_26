"""modulo 8 sorteos

Revision ID: c72e91b4a8f0
Revises: 8d4f2a7c91b3
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c72e91b4a8f0"
down_revision: Union[str, None] = "8d4f2a7c91b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sorteos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("cantidad_caballos_sorteados", sa.Integer(), nullable=False),
        sa.Column("cantidad_reservas", sa.Integer(), nullable=False),
        sa.Column("publicado", sa.Boolean(), nullable=False),
        sa.Column("sorteado_en", sa.DateTime(), nullable=False),
        sa.Column("sorteado_por_id", sa.Integer(), nullable=True),
        sa.Column("sorteado_por_nombre", sa.String(length=120), nullable=True),
        sa.Column("publicado_en", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categorias.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fecha_id"],
            ["fechas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sorteado_por_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "fecha_id",
            "categoria_id",
            name="uq_sorteo_fecha_categoria",
        ),
    )
    op.create_index(op.f("ix_sorteos_id"), "sorteos", ["id"], unique=False)
    op.create_index(op.f("ix_sorteos_fecha_id"), "sorteos", ["fecha_id"], unique=False)
    op.create_index(op.f("ix_sorteos_categoria_id"), "sorteos", ["categoria_id"], unique=False)
    op.create_index(op.f("ix_sorteos_publicado"), "sorteos", ["publicado"], unique=False)

    op.create_table(
        "sorteo_detalles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sorteo_id", sa.Integer(), nullable=False),
        sa.Column("jinete_id", sa.Integer(), nullable=True),
        sa.Column("caballo_id", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("palenque", sa.Integer(), nullable=True),
        sa.Column("es_reserva", sa.Boolean(), nullable=False),
        sa.Column("jinete_nombre", sa.String(length=220), nullable=True),
        sa.Column("jinete_localidad", sa.String(length=120), nullable=True),
        sa.Column("caballo_nombre", sa.String(length=160), nullable=False),
        sa.Column("tropilla_nombre", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(
            ["caballo_id"],
            ["caballos.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["jinete_id"],
            ["jinetes.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sorteo_id"],
            ["sorteos.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sorteo_detalles_id"), "sorteo_detalles", ["id"], unique=False)
    op.create_index(op.f("ix_sorteo_detalles_sorteo_id"), "sorteo_detalles", ["sorteo_id"], unique=False)
    op.create_index(op.f("ix_sorteo_detalles_jinete_id"), "sorteo_detalles", ["jinete_id"], unique=False)
    op.create_index(op.f("ix_sorteo_detalles_caballo_id"), "sorteo_detalles", ["caballo_id"], unique=False)
    op.create_index(op.f("ix_sorteo_detalles_es_reserva"), "sorteo_detalles", ["es_reserva"], unique=False)

    op.create_table(
        "sorteo_auditoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("evento", sa.String(length=40), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("usuario_nombre", sa.String(length=120), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categorias.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fecha_id"],
            ["fechas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sorteo_auditoria_id"), "sorteo_auditoria", ["id"], unique=False)
    op.create_index(op.f("ix_sorteo_auditoria_fecha_id"), "sorteo_auditoria", ["fecha_id"], unique=False)
    op.create_index(op.f("ix_sorteo_auditoria_categoria_id"), "sorteo_auditoria", ["categoria_id"], unique=False)
    op.create_index(op.f("ix_sorteo_auditoria_evento"), "sorteo_auditoria", ["evento"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sorteo_auditoria_evento"), table_name="sorteo_auditoria")
    op.drop_index(op.f("ix_sorteo_auditoria_categoria_id"), table_name="sorteo_auditoria")
    op.drop_index(op.f("ix_sorteo_auditoria_fecha_id"), table_name="sorteo_auditoria")
    op.drop_index(op.f("ix_sorteo_auditoria_id"), table_name="sorteo_auditoria")
    op.drop_table("sorteo_auditoria")

    op.drop_index(op.f("ix_sorteo_detalles_es_reserva"), table_name="sorteo_detalles")
    op.drop_index(op.f("ix_sorteo_detalles_caballo_id"), table_name="sorteo_detalles")
    op.drop_index(op.f("ix_sorteo_detalles_jinete_id"), table_name="sorteo_detalles")
    op.drop_index(op.f("ix_sorteo_detalles_sorteo_id"), table_name="sorteo_detalles")
    op.drop_index(op.f("ix_sorteo_detalles_id"), table_name="sorteo_detalles")
    op.drop_table("sorteo_detalles")

    op.drop_index(op.f("ix_sorteos_publicado"), table_name="sorteos")
    op.drop_index(op.f("ix_sorteos_categoria_id"), table_name="sorteos")
    op.drop_index(op.f("ix_sorteos_fecha_id"), table_name="sorteos")
    op.drop_index(op.f("ix_sorteos_id"), table_name="sorteos")
    op.drop_table("sorteos")
