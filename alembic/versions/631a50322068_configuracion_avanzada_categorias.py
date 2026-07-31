"""configuracion avanzada categorias

Revision ID: 631a50322068
Revises: 412d5d893e0b
Create Date: 2026-07-30 21:51:02.029895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '631a50322068'
down_revision: Union[str, Sequence[str], None] = '412d5d893e0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categorias",
        sa.Column(
            "puntua_campeonato",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "cantidad_montas",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "tipo_monta",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "edad_minima",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "edad_maxima",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "peso_minimo",
            sa.Numeric(precision=6, scale=2),
            nullable=True,
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "peso_maximo",
            sa.Numeric(precision=6, scale=2),
            nullable=True,
        ),
    )

    op.add_column(
        "categorias",
        sa.Column(
            "reglamento",
            sa.Text(),
            nullable=True,
        ),
    )

    # Quitamos los defaults de base de datos.
    # Los defaults futuros quedan manejados por SQLAlchemy.
    with op.batch_alter_table("categorias") as batch_op:
        batch_op.alter_column(
            "puntua_campeonato",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )

        batch_op.alter_column(
            "cantidad_montas",
            existing_type=sa.Integer(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("categorias") as batch_op:
        batch_op.drop_column("reglamento")
        batch_op.drop_column("peso_maximo")
        batch_op.drop_column("peso_minimo")
        batch_op.drop_column("edad_maxima")
        batch_op.drop_column("edad_minima")
        batch_op.drop_column("tipo_monta")
        batch_op.drop_column("cantidad_montas")
        batch_op.drop_column("puntua_campeonato")
