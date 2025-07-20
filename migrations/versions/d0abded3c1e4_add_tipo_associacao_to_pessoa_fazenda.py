# migrations/versions/d0abded3c1e4_add_tipo_associacao_to_pessoa_fazenda.py

"""Add tipo_associacao to pessoa_fazenda

Revision ID: d0abded3c1e4
Revises: a77f98f7c9f2
Create Date: 2025-07-20 18:05:38.011972

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd0abded3c1e4'
down_revision = 'a77f98f7c9f2'
branch_labels = None
depends_on = None

def upgrade():
    # Só adiciona a coluna se ela não existir (safe for multiple runs)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("pessoa_fazenda")]
    if "tipo_associacao" not in columns:
        with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
            batch_op.add_column(sa.Column('tipo_associacao', sa.String(length=50), nullable=False, server_default='Proprietário'))

def downgrade():
    # Só remove a coluna se ela existir
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("pessoa_fazenda")]
    if "tipo_associacao" in columns:
        with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
            batch_op.drop_column('tipo_associacao')