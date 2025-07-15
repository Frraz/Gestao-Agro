"""Add notification tables

Revision ID: bcb479914837
Revises: 04fdeac0e70f
Create Date: 2025-07-14 21:40:09.219320

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'bcb479914837'
down_revision = '04fdeac0e70f'
branch_labels = None
depends_on = None

def upgrade():
    # Cria auditoria apenas se não existir
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'auditoria' not in inspector.get_table_names():
        op.create_table('auditoria',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('usuario_id', sa.Integer(), nullable=True),
            sa.Column('username', sa.String(length=150), nullable=True),
            sa.Column('acao', sa.String(length=100), nullable=False),
            sa.Column('entidade', sa.String(length=100), nullable=True),
            sa.Column('valor_anterior', sa.Text(), nullable=True),
            sa.Column('valor_novo', sa.Text(), nullable=True),
            sa.Column('detalhes', sa.Text(), nullable=True),
            sa.Column('ip', sa.String(length=45), nullable=True),
            sa.Column('data_hora', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    op.create_table('historico_notificacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endividamento_id', sa.Integer(), nullable=False),
        sa.Column('tipo_notificacao', sa.String(length=20), nullable=False),
        sa.Column('data_envio', sa.DateTime(), nullable=True),
        sa.Column('emails_enviados', sa.Text(), nullable=False),
        sa.Column('sucesso', sa.Boolean(), nullable=True),
        sa.Column('erro_mensagem', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['endividamento_id'], ['endividamento.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('notificacao_endividamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endividamento_id', sa.Integer(), nullable=False),
        sa.Column('emails', sa.Text(), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['endividamento_id'], ['endividamento.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pessoa_fazenda',
        sa.Column('pessoa_id', sa.Integer(), nullable=False),
        sa.Column('fazenda_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['fazenda_id'], ['fazenda.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pessoa_id'], ['pessoa.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('pessoa_id', 'fazenda_id')
    )
    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        batch_op.create_index('idx_pessoa_fazenda', ['pessoa_id', 'fazenda_id'], unique=False)

    with op.batch_alter_table('documento', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_documento_data_vencimento'))
        batch_op.drop_index(batch_op.f('idx_documento_tipo'))

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_endividamento_banco'))
        batch_op.drop_index(batch_op.f('idx_endividamento_created_at'))
        batch_op.drop_index(batch_op.f('idx_endividamento_data_vencimento'))

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_parcela_data_vencimento'))
        batch_op.drop_index(batch_op.f('idx_parcela_endividamento_id'))
        batch_op.drop_index(batch_op.f('idx_parcela_pago'))

    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_pessoa_cpf_cnpj'))
        batch_op.drop_index(batch_op.f('idx_pessoa_nome'))

def downgrade():
    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_pessoa_nome'), ['nome'], unique=False)
        batch_op.create_index(batch_op.f('idx_pessoa_cpf_cnpj'), ['cpf_cnpj'], unique=False)

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_parcela_pago'), ['pago'], unique=False)
        batch_op.create_index(batch_op.f('idx_parcela_endividamento_id'), ['endividamento_id'], unique=False)
        batch_op.create_index(batch_op.f('idx_parcela_data_vencimento'), ['data_vencimento'], unique=False)

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_endividamento_data_vencimento'), ['data_vencimento_final'], unique=False)
        batch_op.create_index(batch_op.f('idx_endividamento_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('idx_endividamento_banco'), ['banco'], unique=False)

    with op.batch_alter_table('documento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_documento_tipo'), ['tipo'], unique=False)
        batch_op.create_index(batch_op.f('idx_documento_data_vencimento'), ['data_vencimento'], unique=False)

    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        batch_op.drop_index('idx_pessoa_fazenda')

    op.drop_table('pessoa_fazenda')
    op.drop_table('notificacao_endividamento')
    op.drop_table('historico_notificacao')
    op.drop_table('auditoria')
    