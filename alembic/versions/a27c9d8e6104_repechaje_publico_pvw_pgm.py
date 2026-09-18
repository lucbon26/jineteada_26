"""Clasificación independiente, información pública y snapshots TV."""
from alembic import op
import sqlalchemy as sa

revision = "a27c9d8e6104"
down_revision = "f6b1c92e4d70"
branch_labels = None
depends_on = None

CAMPOS = {
    "jinetes": [("estado_causa", sa.String(60))],
    "jinete_campeonatos": [("estado_clasificacion", sa.String(20)), ("causa_clasificacion", sa.String(60)), ("categoria_clasificacion_id", sa.Integer())],
    "campeonatos": [("informacion_publica", sa.Text()), ("reglamento_publico", sa.Text()), ("documento_url", sa.String(500))],
    "categorias": [("equipamiento", sa.Text())],
    "fechas": [("estado_publico_manual", sa.String(30))],
    "tv_salidas": [(f"{tipo}_{bus}", sa.Text()) for tipo in ("graph", "ticker", "sorteo", "campeonato") for bus in ("pvw", "pgm")],
}

def upgrade():
    for tabla, campos in CAMPOS.items():
        for nombre, tipo in campos:
            op.add_column(tabla, sa.Column(nombre, tipo, nullable=True))
    op.add_column("campeonatos", sa.Column("publicado", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Conservar la visibilidad oficial preexistente; los nuevos nacen privados.
    op.execute(sa.text("UPDATE campeonatos SET publicado = true WHERE modo_prueba = false AND estado IN ('activo', 'finalizado')"))
    # Nunca atribuir a puntos una sanción histórica de causa desconocida.
    op.execute(sa.text("UPDATE jinetes SET estado_causa = 'historica_sin_causa' WHERE estado <> 'activo'"))

def downgrade():
    with op.batch_alter_table("campeonatos") as batch:
        batch.drop_column("publicado")
    for tabla, campos in reversed(list(CAMPOS.items())):
        with op.batch_alter_table(tabla) as batch:
            for nombre, _ in reversed(campos):
                batch.drop_column(nombre)
