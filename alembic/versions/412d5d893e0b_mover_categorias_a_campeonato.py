"""mover categorias a campeonato

Revision ID: 412d5d893e0b
Revises: a3e4866dd6d7
Create Date: 2026-07-30 21:36:47.785069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '412d5d893e0b'
down_revision: Union[str, Sequence[str], None] = 'a3e4866dd6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conexion = op.get_bind()

    # Elimina una posible tabla temporal dejada por el intento fallido.
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_categorias")

    inspector = sa.inspect(conexion)

    columnas = {
        columna["name"]
        for columna in inspector.get_columns("categorias")
    }

    # Agrega campeonato_id solamente si todavía no existe.
    if "campeonato_id" not in columnas:
        op.add_column(
            "categorias",
            sa.Column(
                "campeonato_id",
                sa.Integer(),
                nullable=True,
            ),
        )

    inspector = sa.inspect(conexion)

    columnas = {
        columna["name"]
        for columna in inspector.get_columns("categorias")
    }

    # Si todavía existe fecha_id, trasladamos los datos.
    if "fecha_id" in columnas:
        op.execute(
            """
            UPDATE categorias
            SET campeonato_id = (
                SELECT fechas.campeonato_id
                FROM fechas
                WHERE fechas.id = categorias.fecha_id
            )
            WHERE campeonato_id IS NULL
            """
        )

        indices = {
            indice["name"]
            for indice in inspector.get_indexes("categorias")
        }

        # Hay que borrar el índice antes de eliminar fecha_id.
        if "ix_categorias_fecha_id" in indices:
            op.drop_index(
                "ix_categorias_fecha_id",
                table_name="categorias",
            )

        claves_foraneas = inspector.get_foreign_keys("categorias")

        tiene_fk_campeonato = any(
            fk.get("constrained_columns") == ["campeonato_id"]
            for fk in claves_foraneas
        )

        with op.batch_alter_table(
            "categorias",
            recreate="always",
        ) as batch_op:
            if not tiene_fk_campeonato:
                batch_op.create_foreign_key(
                    "fk_categorias_campeonato_id",
                    "campeonatos",
                    ["campeonato_id"],
                    ["id"],
                    ondelete="CASCADE",
                )

            batch_op.alter_column(
                "campeonato_id",
                existing_type=sa.Integer(),
                nullable=False,
            )

            batch_op.drop_column("fecha_id")

    else:
        # El intento anterior puede haber eliminado fecha_id antes de fallar.
        inspector = sa.inspect(conexion)

        claves_foraneas = inspector.get_foreign_keys("categorias")

        tiene_fk_campeonato = any(
            fk.get("constrained_columns") == ["campeonato_id"]
            for fk in claves_foraneas
        )

        columna_campeonato = next(
            columna
            for columna in inspector.get_columns("categorias")
            if columna["name"] == "campeonato_id"
        )

        requiere_reconstruccion = (
            columna_campeonato["nullable"]
            or not tiene_fk_campeonato
        )

        if requiere_reconstruccion:
            with op.batch_alter_table(
                "categorias",
                recreate="always",
            ) as batch_op:
                if not tiene_fk_campeonato:
                    batch_op.create_foreign_key(
                        "fk_categorias_campeonato_id",
                        "campeonatos",
                        ["campeonato_id"],
                        ["id"],
                        ondelete="CASCADE",
                    )

                batch_op.alter_column(
                    "campeonato_id",
                    existing_type=sa.Integer(),
                    nullable=False,
                )

    # Crear el índice nuevo solamente si no existe.
    inspector = sa.inspect(conexion)

    indices = {
        indice["name"]
        for indice in inspector.get_indexes("categorias")
    }

    if "ix_categorias_campeonato_id" not in indices:
        op.create_index(
            "ix_categorias_campeonato_id",
            "categorias",
            ["campeonato_id"],
            unique=False,
        )


def downgrade() -> None:
    op.add_column(
        "categorias",
        sa.Column(
            "fecha_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # En una reversión, asignamos cada categoría
    # a la primera fecha disponible del campeonato.
    op.execute(
        """
        UPDATE categorias
        SET fecha_id = (
            SELECT MIN(fechas.id)
            FROM fechas
            WHERE fechas.campeonato_id = categorias.campeonato_id
        )
        """
    )

    with op.batch_alter_table("categorias") as batch_op:
        batch_op.create_foreign_key(
            "fk_categorias_fecha_id",
            "fechas",
            ["fecha_id"],
            ["id"],
            ondelete="CASCADE",
        )

        batch_op.alter_column(
            "fecha_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

        batch_op.drop_column("campeonato_id")

    op.create_index(
        "ix_categorias_fecha_id",
        "categorias",
        ["fecha_id"],
        unique=False,
    )
