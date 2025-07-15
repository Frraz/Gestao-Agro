"""fix auditoria idempotente

Revision ID: 4db4f85650c4
Revises: f0898c3bfea6
Create Date: 2025-07-15 01:28:33.088174

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '4db4f85650c4'
down_revision = 'f0898c3bfea6'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    if "auditoria" not in inspector.get_table_names():
        op.create_table(
            "auditoria",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('usuario_id', sa.Integer()),
            sa.Column('username', sa.String(length=150), nullable=True),
            sa.Column('acao', sa.String(length=100), nullable=False),
            sa.Column('entidade', sa.String(length=100), nullable=True),
            sa.Column('valor_anterior', sa.Text(), nullable=True),
            sa.Column('valor_novo', sa.Text(), nullable=True),
            sa.Column('detalhes', sa.Text(), nullable=True),
            sa.Column('ip', sa.String(length=45), nullable=True),
            sa.Column('data_hora', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id']),
        )

def downgrade():
    op.drop_table("auditoria")