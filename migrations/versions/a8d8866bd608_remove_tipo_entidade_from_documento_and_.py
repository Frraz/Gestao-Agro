# /migrations/versions/a8d8866bd608_remove_tipo_entidade_from_documento_and_.py

"""Remove tipo_entidade from documento and allow fazenda_id/pessoa_id nullable

Revision ID: a8d8866bd608
Revises: bcb479914837
Create Date: 2025-07-14 22:55:36.039942

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8d8866bd608'
down_revision = 'bcb479914837'
branch_labels = None
depends_on = None


def upgrade():
    # Remover a coluna tipo_entidade, se existir
    with op.batch_alter_table('documento') as batch_op:
        # O drop só funciona se a coluna existir, ajuste se ela já tiver sido removida
        batch_op.drop_column('tipo_entidade')
        batch_op.alter_column('fazenda_id', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('pessoa_id', existing_type=sa.Integer(), nullable=True)

def downgrade():
    # Adicionar a coluna tipo_entidade de volta, se precisar reverter
    tipo_entidade_enum = sa.Enum('Fazenda', 'Pessoa', name='tipoentidade')
    with op.batch_alter_table('documento') as batch_op:
        batch_op.add_column(sa.Column('tipo_entidade', tipo_entidade_enum, nullable=True))
        batch_op.alter_column('fazenda_id', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('pessoa_id', existing_type=sa.Integer(), nullable=True)