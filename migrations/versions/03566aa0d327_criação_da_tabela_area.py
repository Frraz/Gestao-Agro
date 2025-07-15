"""Criação da tabela area

Revision ID: 03566aa0d327
Revises: e074a214491e
Create Date: 2025-07-14 23:59:00.870280

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03566aa0d327'
down_revision = 'e074a214491e'
branch_labels = None
depends_on = None


def upgrade():
    # Só cria a tabela se ela não existir
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'area' not in inspector.get_table_names():
        op.create_table(
            'area',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('fazenda_id', sa.Integer(), nullable=False),
            sa.Column('nome', sa.String(length=255), nullable=False),
            sa.Column('hectares', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('tipo', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['fazenda_id'], ['fazenda.id']),
            sa.PrimaryKeyConstraint('id')
        )

    if 'endividamento_area' not in inspector.get_table_names():
        op.create_table(
            'endividamento_area',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('endividamento_id', sa.Integer(), nullable=False),
            sa.Column('area_id', sa.Integer(), nullable=False),
            sa.Column('tipo', sa.String(length=50), nullable=False),
            sa.Column('hectares_utilizados', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.ForeignKeyConstraint(['area_id'], ['area.id']),
            sa.ForeignKeyConstraint(['endividamento_id'], ['endividamento.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # Remoção dos índices para facilitar alterações de schema
    with op.batch_alter_table('documento', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('idx_documento_data_vencimento'))
        except Exception:
            pass
        try:
            batch_op.drop_index(batch_op.f('idx_documento_tipo'))
        except Exception:
            pass

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('idx_endividamento_banco'))
        except Exception:
            pass
        try:
            batch_op.drop_index(batch_op.f('idx_endividamento_created_at'))
        except Exception:
            pass
        try:
            batch_op.drop_index(batch_op.f('idx_endividamento_data_vencimento'))
        except Exception:
            pass

    with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('idx_historico_notificacao_data'))
        except Exception:
            pass

    with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('idx_notificacao_endividamento_ativo'))
        except Exception:
            pass

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('idx_parcela_data_vencimento'))
        except Exception:
            pass
        # NÃO remova o índice idx_parcela_endividamento_id, pois é usado em uma FK!
        # try:
        #     batch_op.drop_index(batch_op.f('idx_parcela_endividamento_id'))
        # except Exception:
        #     pass
        try:
            batch_op.drop_index(batch_op.f('idx_parcela_pago'))
        except Exception:
            pass

    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('idx_pessoa_cpf_cnpj'))
        except Exception:
            pass
        try:
            batch_op.drop_index(batch_op.f('idx_pessoa_nome'))
        except Exception:
            pass


def downgrade():
    # Recriação dos índices removidos
    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        try:
            batch_op.create_index(batch_op.f('idx_pessoa_nome'), ['nome'], unique=False)
        except Exception:
            pass
        try:
            batch_op.create_index(batch_op.f('idx_pessoa_cpf_cnpj'), ['cpf_cnpj'], unique=False)
        except Exception:
            pass

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        try:
            batch_op.create_index(batch_op.f('idx_parcela_pago'), ['pago'], unique=False)
        except Exception:
            pass
        # Não tente recriar o índice idx_parcela_endividamento_id manualmente, pois é gerenciado pela FK
        try:
            batch_op.create_index(batch_op.f('idx_parcela_data_vencimento'), ['data_vencimento'], unique=False)
        except Exception:
            pass

    with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
        try:
            batch_op.create_index(batch_op.f('idx_notificacao_endividamento_ativo'), ['ativo'], unique=False)
        except Exception:
            pass

    with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
        try:
            batch_op.create_index(batch_op.f('idx_historico_notificacao_data'), ['data_envio'], unique=False)
        except Exception:
            pass

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        try:
            batch_op.create_index(batch_op.f('idx_endividamento_data_vencimento'), ['data_vencimento_final'], unique=False)
        except Exception:
            pass
        try:
            batch_op.create_index(batch_op.f('idx_endividamento_created_at'), ['created_at'], unique=False)
        except Exception:
            pass
        try:
            batch_op.create_index(batch_op.f('idx_endividamento_banco'), ['banco'], unique=False)
        except Exception:
            pass

    with op.batch_alter_table('documento', schema=None) as batch_op:
        try:
            batch_op.create_index(batch_op.f('idx_documento_tipo'), ['tipo'], unique=False)
        except Exception:
            pass
        try:
            batch_op.create_index(batch_op.f('idx_documento_data_vencimento'), ['data_vencimento'], unique=False)
        except Exception:
            pass

    # Remoção das tabelas criadas
    op.drop_table('endividamento_area')
    op.drop_table('area')