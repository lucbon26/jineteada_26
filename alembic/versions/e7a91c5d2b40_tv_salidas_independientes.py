"""TV: salidas independientes, preview y ajustes operativos

Revision ID: e7a91c5d2b40
Revises: c3d8f1a6b274
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7a91c5d2b40"
down_revision: Union[str, Sequence[str], None] = "c3d8f1a6b274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tv_salidas") as batch_op:
        batch_op.add_column(sa.Column("graph_sorteo_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ticker_sorteo_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("tabla_sorteo_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("campeonato_sorteo_id", sa.Integer(), nullable=True))

        batch_op.add_column(sa.Column("graph_al_aire", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("ticker_al_aire", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("tabla_sorteo_al_aire", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("tabla_campeonato_al_aire", sa.Boolean(), nullable=False, server_default=sa.false()))

        batch_op.add_column(sa.Column("graph_mostrar_jinete", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("graph_mostrar_localidad", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("graph_mostrar_caballo", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("graph_mostrar_palenque", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("graph_mostrar_categoria", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("graph_override_palenque", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("graph_override_caballo", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("palenques_tv_json", sa.Text(), nullable=False, server_default="{}"))

        batch_op.create_foreign_key("fk_tv_salidas_graph_sorteo", "sorteos", ["graph_sorteo_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tv_salidas_ticker_sorteo", "sorteos", ["ticker_sorteo_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tv_salidas_tabla_sorteo", "sorteos", ["tabla_sorteo_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_tv_salidas_campeonato_sorteo", "sorteos", ["campeonato_sorteo_id"], ["id"], ondelete="SET NULL")

    # Conservar la selección previa como punto de partida de las cuatro previews,
    # pero todas las salidas quedan apagadas por seguridad.
    op.execute(
        "UPDATE tv_salidas SET "
        "graph_sorteo_id = sorteo_id, "
        "ticker_sorteo_id = sorteo_id, "
        "tabla_sorteo_id = sorteo_id, "
        "campeonato_sorteo_id = sorteo_id"
    )


def downgrade() -> None:
    with op.batch_alter_table("tv_salidas") as batch_op:
        batch_op.drop_constraint("fk_tv_salidas_campeonato_sorteo", type_="foreignkey")
        batch_op.drop_constraint("fk_tv_salidas_tabla_sorteo", type_="foreignkey")
        batch_op.drop_constraint("fk_tv_salidas_ticker_sorteo", type_="foreignkey")
        batch_op.drop_constraint("fk_tv_salidas_graph_sorteo", type_="foreignkey")

        batch_op.drop_column("palenques_tv_json")
        batch_op.drop_column("graph_override_caballo")
        batch_op.drop_column("graph_override_palenque")
        batch_op.drop_column("graph_mostrar_categoria")
        batch_op.drop_column("graph_mostrar_palenque")
        batch_op.drop_column("graph_mostrar_caballo")
        batch_op.drop_column("graph_mostrar_localidad")
        batch_op.drop_column("graph_mostrar_jinete")

        batch_op.drop_column("tabla_campeonato_al_aire")
        batch_op.drop_column("tabla_sorteo_al_aire")
        batch_op.drop_column("ticker_al_aire")
        batch_op.drop_column("graph_al_aire")

        batch_op.drop_column("campeonato_sorteo_id")
        batch_op.drop_column("tabla_sorteo_id")
        batch_op.drop_column("ticker_sorteo_id")
        batch_op.drop_column("graph_sorteo_id")
