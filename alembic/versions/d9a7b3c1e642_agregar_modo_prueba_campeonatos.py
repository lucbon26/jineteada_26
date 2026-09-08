"""agregar modo prueba a campeonatos
Revision ID: d9a7b3c1e642
Revises: c72e91b4a8f0
"""
from alembic import op
import sqlalchemy as sa
revision = "d9a7b3c1e642"
down_revision = "c72e91b4a8f0"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("campeonatos") as batch_op:
        batch_op.add_column(sa.Column("modo_prueba", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_campeonatos_modo_prueba", ["modo_prueba"], unique=False)

def downgrade():
    with op.batch_alter_table("campeonatos") as batch_op:
        batch_op.drop_index("ix_campeonatos_modo_prueba")
        batch_op.drop_column("modo_prueba")
