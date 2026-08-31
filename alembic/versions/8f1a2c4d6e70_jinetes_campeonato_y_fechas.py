
"""jinetes por campeonato y fechas

Revision ID: 8f1a2c4d6e70
Revises: 5b7d9c2e4a10
Create Date: 2026-08-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1a2c4d6e70"
down_revision: Union[str, None] = "5b7d9c2e4a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jinete_campeonatos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jinete_id", sa.Integer(), nullable=False),
        sa.Column("campeonato_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["jinete_id"],
            ["jinetes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campeonato_id"],
            ["campeonatos.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categorias.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "jinete_id",
            "campeonato_id",
            name="uq_jinete_campeonato",
        ),
    )

    op.create_index(
        op.f("ix_jinete_campeonatos_jinete_id"),
        "jinete_campeonatos",
        ["jinete_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_jinete_campeonatos_campeonato_id"),
        "jinete_campeonatos",
        ["campeonato_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_jinete_campeonatos_categoria_id"),
        "jinete_campeonatos",
        ["categoria_id"],
        unique=False,
    )

    op.create_table(
        "jinete_fechas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jinete_id", sa.Integer(), nullable=False),
        sa.Column("fecha_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["jinete_id"],
            ["jinetes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fecha_id"],
            ["fechas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categorias.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "jinete_id",
            "fecha_id",
            name="uq_jinete_fecha",
        ),
    )

    op.create_index(
        op.f("ix_jinete_fechas_jinete_id"),
        "jinete_fechas",
        ["jinete_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_jinete_fechas_fecha_id"),
        "jinete_fechas",
        ["fecha_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_jinete_fechas_categoria_id"),
        "jinete_fechas",
        ["categoria_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_jinete_fechas_categoria_id"),
        table_name="jinete_fechas",
    )
    op.drop_index(
        op.f("ix_jinete_fechas_fecha_id"),
        table_name="jinete_fechas",
    )
    op.drop_index(
        op.f("ix_jinete_fechas_jinete_id"),
        table_name="jinete_fechas",
    )
    op.drop_table("jinete_fechas")

    op.drop_index(
        op.f("ix_jinete_campeonatos_categoria_id"),
        table_name="jinete_campeonatos",
    )
    op.drop_index(
        op.f("ix_jinete_campeonatos_campeonato_id"),
        table_name="jinete_campeonatos",
    )
    op.drop_index(
        op.f("ix_jinete_campeonatos_jinete_id"),
        table_name="jinete_campeonatos",
    )
    op.drop_table("jinete_campeonatos")
