"""Repechaje separado de F3, sin trasladar puntos de fechas oficiales."""
from alembic import op
import sqlalchemy as sa

revision = 'b38da91f7205'
down_revision = 'a27c9d8e6104'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('repechajes_categorias',
        sa.Column('categoria_id', sa.Integer(), sa.ForeignKey('categorias.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('estado', sa.String(20), nullable=False),
        sa.Column('base_firma', sa.String(64), nullable=False),
        sa.Column('puntos_json', sa.Text(), nullable=False),
        sa.Column('confirmado_en', sa.DateTime(), nullable=True),
        sa.Column('confirmado_por', sa.String(150), nullable=True),
    )
    # Sólo descartar el cálculo que provenía de interpretar F3 como repechaje.
    # No se modifica jinetes.estado, sus sanciones, puntajes ni sorteos.
    op.execute(sa.text("UPDATE jinete_campeonatos SET estado_clasificacion = NULL, causa_clasificacion = NULL WHERE causa_clasificacion = 'puntos_f3'"))


def downgrade():
    op.execute(sa.text("UPDATE jinete_campeonatos SET estado_clasificacion = NULL, causa_clasificacion = NULL WHERE causa_clasificacion = 'puntos_repechaje'"))
    op.drop_table('repechajes_categorias')
