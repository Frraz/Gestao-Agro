# /migrations/versions/e8f35fa3c7ce_.py

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
    # MIGRATION INICIAL: NÃO USE DROP_INDEX, DROP_COLUMN, NEM NADA DE REMOÇÃO!
    # Se suas tabelas já existem, deixe vazio.
    # Se quiser criar tabelas com Alembic, gere uma nova migration com flask db migrate.
    pass

def downgrade():
    pass