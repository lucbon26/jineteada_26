"""modulo 7 inscripciones qr

Revision ID: 8d4f2a7c91b3
Revises: 5b7d9c2e4a10
Create Date: 2026-08-30
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "8d4f2a7c91b3"
down_revision: Union[str, Sequence[str], None] = "8f1a2c4d6e70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("jinetes") as batch_op:
        batch_op.add_column(
            sa.Column("qr_token", sa.String(length=80), nullable=True)
        )

    conexion = op.get_bind()
    filas = conexion.execute(sa.text("SELECT id FROM jinetes")).fetchall()
    for fila in filas:
        conexion.execute(
            sa.text("UPDATE jinetes SET qr_token = :token WHERE id = :id"),
            {"token": uuid.uuid4().hex + uuid.uuid4().hex[:8], "id": fila.id},
        )

    with op.batch_alter_table("jinetes") as batch_op:
        batch_op.alter_column(
            "qr_token",
            existing_type=sa.String(length=80),
            nullable=False,
        )
        batch_op.create_index("ix_jinetes_qr_token", ["qr_token"], unique=True)

    with op.batch_alter_table("jinete_fechas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "estado",
                sa.String(length=30),
                nullable=False,
                server_default="pendiente",
            )
        )
        batch_op.add_column(
            sa.Column("motivo_no_habilitado", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(sa.Column("validado_en", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("validado_por", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(sa.Column("observaciones", sa.Text(), nullable=True))
        batch_op.create_index("ix_jinete_fechas_estado", ["estado"], unique=False)

    with op.batch_alter_table("jinete_fechas") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=sa.String(length=30),
            server_default=None,
        )

    with op.batch_alter_table("fechas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "inscripcion_cerrada",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("inscripcion_cerrada_en", sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table("fechas") as batch_op:
        batch_op.alter_column(
            "inscripcion_cerrada",
            existing_type=sa.Boolean(),
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("fechas") as batch_op:
        batch_op.drop_column("inscripcion_cerrada_en")
        batch_op.drop_column("inscripcion_cerrada")

    with op.batch_alter_table("jinete_fechas") as batch_op:
        batch_op.drop_index("ix_jinete_fechas_estado")
        batch_op.drop_column("observaciones")
        batch_op.drop_column("validado_por")
        batch_op.drop_column("validado_en")
        batch_op.drop_column("motivo_no_habilitado")
        batch_op.drop_column("estado")

    with op.batch_alter_table("jinetes") as batch_op:
        batch_op.drop_index("ix_jinetes_qr_token")
        batch_op.drop_column("qr_token")
