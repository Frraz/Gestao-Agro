"""empty message

Revision ID: e8f35fa3c7ce
Revises: 
Create Date: 2025-06-14 21:53:19.232366

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e8f35fa3c7ce'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Migration inicial: não deve conter drop_index/drop_column.
    pass

def downgrade():
    # Migration inicial: normalmente vazio, ou DROP TABLE das tabelas criadas.
    pass