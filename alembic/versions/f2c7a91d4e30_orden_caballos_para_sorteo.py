"""orden caballos para sorteo

Revision ID: f2c7a91d4e30
Revises: e4b8c2d6f901
"""

from alembic import op
import sqlalchemy as sa

revision = "f2c7a91d4e30"
down_revision = "e4b8c2d6f901"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "caballos_fechas",
        sa.Column("orden_carga", sa.Integer(), nullable=True),
    )
    op.add_column(
        "caballos_fechas",
        sa.Column(
            "aleatorizar_sorteo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    # Las asignaciones existentes conservan su orden histórico por id.
    conexion = op.get_bind()
    filas = conexion.execute(
        sa.text(
            "SELECT id, fecha_id, categoria_id "
            "FROM caballos_fechas "
            "ORDER BY fecha_id, categoria_id, id"
        )
    ).fetchall()

    contadores = {}
    for fila in filas:
        clave = (fila.fecha_id, fila.categoria_id)
        contadores[clave] = contadores.get(clave, 0) + 1
        conexion.execute(
            sa.text(
                "UPDATE caballos_fechas "
                "SET orden_carga = :orden WHERE id = :id"
            ),
            {"orden": contadores[clave], "id": fila.id},
        )


def downgrade():
    op.drop_column("caballos_fechas", "aleatorizar_sorteo")
    op.drop_column("caballos_fechas", "orden_carga")
