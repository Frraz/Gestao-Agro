# migrations/versions/a77f98f7c9f2_add_field_ativo_and_other_user_fields.py

"""Add field ativo and other user fields

Revision ID: a77f98f7c9f2
Revises: e8d2ebcf51cd
Create Date: 2025-07-20 15:27:03.821534

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a77f98f7c9f2'
down_revision = 'e8d2ebcf51cd'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('documento', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_documento_data_vencimento'))
        batch_op.drop_index(batch_op.f('idx_documento_processamento'))
        batch_op.drop_index(batch_op.f('idx_documento_tipo'))
        batch_op.drop_index(batch_op.f('idx_documento_vencimento_status'))

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_endividamento_banco'))
        batch_op.drop_index(batch_op.f('idx_endividamento_data_vencimento'))

    with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
        batch_op.alter_column('sucesso',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=False)
        batch_op.drop_index(batch_op.f('idx_historico_notificacao_data'))
        batch_op.drop_constraint('historico_notificacao_ibfk_1', type_='foreignkey')
        batch_op.drop_index(batch_op.f('idx_historico_notificacao_endividamento'))
        batch_op.create_foreign_key(None, 'notificacao_endividamento', ['notificacao_id'], ['id'])

    with op.batch_alter_table('historico_notificacao_documento', schema=None) as batch_op:
        batch_op.drop_index('idx_historico_notificacao_documento')

    with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
        batch_op.alter_column('data_envio',
               existing_type=mysql.DATETIME(),
               nullable=True)
        batch_op.drop_index(batch_op.f('idx_notificacao_endividamento_ativo'))
        batch_op.drop_index(batch_op.f('idx_notificacao_endividamento_data_envio'))
        batch_op.drop_index(batch_op.f('idx_notificacao_endividamento_enviado'))
        batch_op.drop_index(batch_op.f('idx_notificacao_endividamento_tipo'))
        batch_op.drop_index(batch_op.f('idx_notificacao_pendente'))
        batch_op.drop_constraint(batch_op.f('notificacao_endividamento_ibfk_1'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'endividamento', ['endividamento_id'], ['id'], ondelete='CASCADE')
        # Remova os drop_column abaixo se as colunas já não existem
        # batch_op.drop_column('conteudo')
        # batch_op.drop_column('data_criacao')
        # batch_op.drop_column('data_atualizacao')
        # batch_op.drop_column('destinatarios')
        # batch_op.drop_column('fazenda_id')

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_parcela_data_vencimento'))

        batch_op.drop_index(batch_op.f('idx_parcela_pago'))

    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('idx_pessoa_cpf_cnpj'))
        batch_op.drop_index(batch_op.f('idx_pessoa_nome'))

    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        #batch_op.drop_index(batch_op.f('idx_pessoa_fazenda_unico'))
        #batch_op.drop_index(batch_op.f('ix_pessoa_fazenda_fazenda_id'))
        #batch_op.drop_index(batch_op.f('ix_pessoa_fazenda_pessoa_id'))
        batch_op.drop_index(batch_op.f('ix_pessoa_fazenda_tipo_posse'))
        batch_op.create_index('idx_pessoa_fazenda', ['pessoa_id', 'fazenda_id'], unique=False)
        batch_op.drop_column('id')
        batch_op.drop_column('tipo_posse')
        batch_op.drop_column('data_inicio')
        batch_op.drop_column('data_fim')

    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('ultimo_login', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('token_recuperacao', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('token_expiracao', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.drop_column('token_expiracao')
        batch_op.drop_column('token_recuperacao')
        batch_op.drop_column('ultimo_login')
        batch_op.drop_column('ativo')

    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_fim', sa.DATE(), nullable=True))
        batch_op.add_column(sa.Column('data_inicio', sa.DATE(), nullable=False))
        batch_op.add_column(sa.Column('tipo_posse', mysql.ENUM('PROPRIA', 'ARRENDADA', 'COMODATO', 'POSSE', collation='utf8mb4_unicode_ci'), server_default=sa.text("'PROPRIA'"), nullable=False))
        batch_op.add_column(sa.Column('id', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.drop_index('idx_pessoa_fazenda')
        batch_op.create_index(batch_op.f('ix_pessoa_fazenda_tipo_posse'), ['tipo_posse'], unique=False)
        #batch_op.create_index(batch_op.f('ix_pessoa_fazenda_pessoa_id'), ['pessoa_id'], unique=False)
        #batch_op.create_index(batch_op.f('ix_pessoa_fazenda_fazenda_id'), ['fazenda_id'], unique=False)
        #batch_op.create_index(batch_op.f('idx_pessoa_fazenda_unico'), ['pessoa_id', 'fazenda_id', 'tipo_posse'], unique=True)

    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_pessoa_nome'), ['nome'], unique=False)
        batch_op.create_index(batch_op.f('idx_pessoa_cpf_cnpj'), ['cpf_cnpj'], unique=False)

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_parcela_pago'), ['pago'], unique=False)
        batch_op.create_index(batch_op.f('idx_parcela_endividamento_id'), ['endividamento_id'], unique=False)
        batch_op.create_index(batch_op.f('idx_parcela_data_vencimento'), ['data_vencimento'], unique=False)

    with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fazenda_id', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.add_column(sa.Column('destinatarios', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=True))
        batch_op.add_column(sa.Column('data_atualizacao', mysql.DATETIME(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=True))
        batch_op.add_column(sa.Column('data_criacao', mysql.DATETIME(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
        batch_op.add_column(sa.Column('conteudo', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=True))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('notificacao_endividamento_ibfk_1'), 'endividamento', ['endividamento_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_notificacao_endividamento_tipo_notificacao'))
        batch_op.drop_index(batch_op.f('ix_notificacao_endividamento_enviado'))
        batch_op.drop_index(batch_op.f('ix_notificacao_endividamento_endividamento_id'))
        batch_op.drop_index(batch_op.f('ix_notificacao_endividamento_data_envio'))
        batch_op.drop_index(batch_op.f('ix_notificacao_endividamento_ativo'))
        batch_op.create_index(batch_op.f('idx_notificacao_pendente'), ['ativo', 'enviado', 'data_envio'], unique=False)
        batch_op.create_index(batch_op.f('idx_notificacao_endividamento_tipo'), ['tipo_notificacao'], unique=False)
        batch_op.create_index(batch_op.f('idx_notificacao_endividamento_enviado'), ['enviado'], unique=False)
        batch_op.create_index(batch_op.f('idx_notificacao_endividamento_data_envio'), ['data_envio'], unique=False)
        batch_op.create_index(batch_op.f('idx_notificacao_endividamento_ativo'), ['ativo'], unique=False)
        batch_op.alter_column('data_envio',
               existing_type=mysql.DATETIME(),
               nullable=True)
        batch_op.alter_column('tipo_notificacao',
               existing_type=sa.String(length=50),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50),
               nullable=True)
        batch_op.drop_column('erro_mensagem')
        batch_op.drop_column('tentativas')

    with op.batch_alter_table('historico_notificacao_documento', schema=None) as batch_op:
        batch_op.add_column(sa.Column('emails_enviados', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=True))
        batch_op.drop_index(batch_op.f('ix_historico_notificacao_documento_documento_id'))
        batch_op.drop_index('idx_historico_notificacao_documento_tipo')
        batch_op.drop_index('idx_historico_notificacao_documento_data')
        batch_op.create_index('idx_historico_notificacao_documento', ['documento_id'], unique=False)
        batch_op.drop_column('erro_mensagem')

    with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_index(batch_op.f('idx_historico_notificacao_endividamento'), ['endividamento_id'], unique=False)
        batch_op.create_index(batch_op.f('idx_historico_notificacao_data'), ['data_envio'], unique=False)
        batch_op.alter_column('sucesso',
               existing_type=mysql.TINYINT(display_width=1),
               nullable=True)
        batch_op.alter_column('tipo_notificacao',
               existing_type=sa.String(length=50),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=20),
               existing_nullable=False)

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_endividamento_data_vencimento'), ['data_vencimento_final'], unique=False)
        batch_op.create_index(batch_op.f('idx_endividamento_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('idx_endividamento_banco'), ['banco'], unique=False)

    with op.batch_alter_table('documento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_documento_vencimento_status'), ['data_vencimento', 'ativo'], unique=False)
        batch_op.create_index(batch_op.f('idx_documento_tipo'), ['tipo'], unique=False)
        batch_op.create_index(batch_op.f('idx_documento_processamento'), ['status_processamento'], unique=False)
        batch_op.create_index(batch_op.f('idx_documento_data_vencimento'), ['data_vencimento'], unique=False)