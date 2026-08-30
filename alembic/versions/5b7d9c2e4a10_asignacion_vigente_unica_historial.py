"""Asignacion vigente unica e historial de caballos

Revision ID: 5b7d9c2e4a10
Revises: 1703d57471b1
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa


revision = "5b7d9c2e4a10"
down_revision = "1703d57471b1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "fechas",
        sa.Column(
            "sorteada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_table(
        "caballos_historial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("caballo_id", sa.Integer(), nullable=False),
        sa.Column("campeonato_id", sa.Integer(), nullable=True),
        sa.Column("fecha_id", sa.Integer(), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("evento", sa.String(length=50), nullable=False),
        sa.Column("estado_caballo", sa.String(length=20), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["caballo_id"],
            ["caballos.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["campeonato_id"], ["campeonatos.id"]),
        sa.ForeignKeyConstraint(["fecha_id"], ["fechas.id"]),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_caballos_historial_caballo_id",
        "caballos_historial",
        ["caballo_id"],
    )
    op.create_index(
        "ix_caballos_historial_campeonato_id",
        "caballos_historial",
        ["campeonato_id"],
    )
    op.create_index(
        "ix_caballos_historial_fecha_id",
        "caballos_historial",
        ["fecha_id"],
    )
    op.create_index(
        "ix_caballos_historial_categoria_id",
        "caballos_historial",
        ["categoria_id"],
    )
    op.create_index(
        "ix_caballos_historial_creado_en",
        "caballos_historial",
        ["creado_en"],
    )

    conexion = op.get_bind()

    filas = conexion.execute(
        sa.text(
            """
            SELECT
                cf.id,
                cf.caballo_id,
                cf.fecha_id,
                cf.categoria_id,
                f.campeonato_id,
                f.fecha
            FROM caballos_fechas AS cf
            JOIN fechas AS f ON f.id = cf.fecha_id
            ORDER BY
                cf.caballo_id,
                f.fecha DESC,
                cf.id DESC
            """
        )
    ).mappings().all()

    por_caballo = {}

    for fila in filas:
        por_caballo.setdefault(
            fila["caballo_id"],
            [],
        ).append(fila)

    for asignaciones in por_caballo.values():
        # Conserva vigente la asignación de la fecha más nueva.
        # Las anteriores quedan registradas como historial.
        for anterior in asignaciones[1:]:
            conexion.execute(
                sa.text(
                    """
                    INSERT INTO caballos_historial (
                        caballo_id,
                        campeonato_id,
                        fecha_id,
                        categoria_id,
                        evento,
                        estado_caballo,
                        observaciones,
                        creado_en
                    )
                    SELECT
                        :caballo_id,
                        :campeonato_id,
                        :fecha_id,
                        :categoria_id,
                        'participacion_archivada',
                        c.estado,
                        'Migrado desde una asignación vigente anterior.',
                        CURRENT_TIMESTAMP
                    FROM caballos AS c
                    WHERE c.id = :caballo_id
                    """
                ),
                {
                    "caballo_id": anterior["caballo_id"],
                    "campeonato_id": anterior["campeonato_id"],
                    "fecha_id": anterior["fecha_id"],
                    "categoria_id": anterior["categoria_id"],
                },
            )

            conexion.execute(
                sa.text(
                    "DELETE FROM caballos_fechas WHERE id = :id"
                ),
                {"id": anterior["id"]},
            )

    with op.batch_alter_table(
        "caballos_fechas",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_caballo_fecha_categoria",
            type_="unique",
        )

        batch_op.create_unique_constraint(
            "uq_caballo_asignacion_vigente",
            ["caballo_id"],
        )


def downgrade():
    with op.batch_alter_table(
        "caballos_fechas",
        schema=None,
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_caballo_asignacion_vigente",
            type_="unique",
        )

        batch_op.create_unique_constraint(
            "uq_caballo_fecha_categoria",
            ["caballo_id", "fecha_id", "categoria_id"],
        )

    op.drop_index(
        "ix_caballos_historial_creado_en",
        table_name="caballos_historial",
    )
    op.drop_index(
        "ix_caballos_historial_categoria_id",
        table_name="caballos_historial",
    )
    op.drop_index(
        "ix_caballos_historial_fecha_id",
        table_name="caballos_historial",
    )
    op.drop_index(
        "ix_caballos_historial_campeonato_id",
        table_name="caballos_historial",
    )
    op.drop_index(
        "ix_caballos_historial_caballo_id",
        table_name="caballos_historial",
    )

    op.drop_table("caballos_historial")

    with op.batch_alter_table("fechas", schema=None) as batch_op:
        batch_op.drop_column("sorteada")
