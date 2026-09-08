"""catalogo global de categorias

Revision ID: e4b8c2d6f901
Revises: d9a7b3c1e642
"""

from alembic import op
import sqlalchemy as sa

revision = "e4b8c2d6f901"
down_revision = "d9a7b3c1e642"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categorias_globales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("nombre", name="uq_categorias_globales_nombre"),
    )
    op.create_index("ix_categorias_globales_id", "categorias_globales", ["id"])
    op.create_index("ix_categorias_globales_nombre", "categorias_globales", ["nombre"], unique=True)

    with op.batch_alter_table("categorias") as batch_op:
        batch_op.add_column(sa.Column("categoria_global_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_categorias_categoria_global_id", ["categoria_global_id"])
        batch_op.create_foreign_key(
            "fk_categorias_categoria_global",
            "categorias_globales",
            ["categoria_global_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Migración de datos existentes: un nombre lógico global por nombre,
    # conservando cada configuración por campeonato.
    conn = op.get_bind()
    filas = conn.execute(sa.text("SELECT id, nombre FROM categorias ORDER BY id")).fetchall()
    globales = {}
    for categoria_id, nombre in filas:
        clave = (nombre or "").strip().lower()
        if clave not in globales:
            result = conn.execute(
                sa.text(
                    "INSERT INTO categorias_globales (nombre, creado_en) "
                    "VALUES (:nombre, CURRENT_TIMESTAMP)"
                ),
                {"nombre": (nombre or "").strip()},
            )
            globales[clave] = result.lastrowid
        conn.execute(
            sa.text(
                "UPDATE categorias SET categoria_global_id=:gid WHERE id=:cid"
            ),
            {"gid": globales[clave], "cid": categoria_id},
        )


def downgrade():
    with op.batch_alter_table("categorias") as batch_op:
        batch_op.drop_constraint("fk_categorias_categoria_global", type_="foreignkey")
        batch_op.drop_index("ix_categorias_categoria_global_id")
        batch_op.drop_column("categoria_global_id")

    op.drop_index("ix_categorias_globales_nombre", table_name="categorias_globales")
    op.drop_index("ix_categorias_globales_id", table_name="categorias_globales")
    op.drop_table("categorias_globales")
