"""estados de jinetes

Revision ID: 20fd1174d91e
Revises: 80a07d64ceb1
Create Date: 2026-08-09 00:53:21.182190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20fd1174d91e'
down_revision: Union[str, Sequence[str], None] = '80a07d64ceb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jinetes",
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default="activo",
        ),
    )

    op.execute(
        """
        UPDATE jinetes
        SET estado = CASE
            WHEN activo = 1 THEN 'activo'
            ELSE 'inactivo'
        END
        """
    )

    with op.batch_alter_table("jinetes") as batch_op:
        batch_op.drop_column("activo")


def downgrade() -> None:
    op.add_column(
        "jinetes",
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.execute(
        """
        UPDATE jinetes
        SET activo = CASE
            WHEN estado = 'activo' THEN 1
            ELSE 0
        END
        """
    )

    with op.batch_alter_table("jinetes") as batch_op:
        batch_op.drop_column("estado")
