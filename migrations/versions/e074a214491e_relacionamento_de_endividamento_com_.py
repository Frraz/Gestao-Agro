# /migrations/versions/e074a214491e_relacionamento_de_endividamento_com_.py

"""Relacionamento de endividamento com áreas

Revision ID: e074a214491e
Revises: a8d8866bd608
Create Date: 2025-07-14 23:36:11.823084

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e074a214491e'
down_revision = 'a8d8866bd608'
branch_labels = None
depends_on = None

def index_exists(connection, table_name, index_name):
    sql = """
    SELECT COUNT(1)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema=DATABASE() AND table_name=:table_name AND index_name=:index_name
    """
    res = connection.execute(sa.text(sql), {'table_name': table_name, 'index_name': index_name})
    return res.scalar() > 0

def upgrade():
    conn = op.get_bind()

    # DOCUMENTO
    if index_exists(conn, 'documento', 'idx_documento_data_vencimento'):
        with op.batch_alter_table('documento', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_documento_data_vencimento'))
    # batch_op.drop_index(batch_op.f('idx_documento_entidade_tipo'))  # NÃO REMOVA OU COMENTE SE DER ERRO!
    if index_exists(conn, 'documento', 'idx_documento_tipo'):
        with op.batch_alter_table('documento', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_documento_tipo'))

    # ENDIVIDAMENTO
    if index_exists(conn, 'endividamento', 'idx_endividamento_banco'):
        with op.batch_alter_table('endividamento', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_endividamento_banco'))
    if index_exists(conn, 'endividamento', 'idx_endividamento_created_at'):
        with op.batch_alter_table('endividamento', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_endividamento_created_at'))
    if index_exists(conn, 'endividamento', 'idx_endividamento_data_vencimento'):
        with op.batch_alter_table('endividamento', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_endividamento_data_vencimento'))

    # HISTORICO_NOTIFICACAO
    if index_exists(conn, 'historico_notificacao', 'idx_historico_notificacao_data'):
        with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_historico_notificacao_data'))

    # NOTIFICACAO_ENDIVIDAMENTO
    if index_exists(conn, 'notificacao_endividamento', 'idx_notificacao_endividamento_ativo'):
        with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_notificacao_endividamento_ativo'))

    # PARCELA
    if index_exists(conn, 'parcela', 'idx_parcela_data_vencimento'):
        with op.batch_alter_table('parcela', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_parcela_data_vencimento'))
    # NÃO REMOVA: índice de FK!
    # if index_exists(conn, 'parcela', 'idx_parcela_endividamento_id'):
    #     with op.batch_alter_table('parcela', schema=None) as batch_op:
    #         batch_op.drop_index(batch_op.f('idx_parcela_endividamento_id'))
    if index_exists(conn, 'parcela', 'idx_parcela_pago'):
        with op.batch_alter_table('parcela', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_parcela_pago'))

    # PESSOA
    if index_exists(conn, 'pessoa', 'idx_pessoa_cpf_cnpj'):
        with op.batch_alter_table('pessoa', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_pessoa_cpf_cnpj'))
    if index_exists(conn, 'pessoa', 'idx_pessoa_nome'):
        with op.batch_alter_table('pessoa', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('idx_pessoa_nome'))

def downgrade():
    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_pessoa_nome'), ['nome'], unique=False)
        batch_op.create_index(batch_op.f('idx_pessoa_cpf_cnpj'), ['cpf_cnpj'], unique=False)

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_parcela_pago'), ['pago'], unique=False)
        batch_op.create_index(batch_op.f('idx_parcela_endividamento_id'), ['endividamento_id'], unique=False)
        batch_op.create_index(batch_op.f('idx_parcela_data_vencimento'), ['data_vencimento'], unique=False)

    with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_notificacao_endividamento_ativo'), ['ativo'], unique=False)

    with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_historico_notificacao_data'), ['data_envio'], unique=False)

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_endividamento_data_vencimento'), ['data_vencimento_final'], unique=False)
        batch_op.create_index(batch_op.f('idx_endividamento_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('idx_endividamento_banco'), ['banco'], unique=False)

    with op.batch_alter_table('documento', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('idx_documento_tipo'), ['tipo'], unique=False)
        batch_op.create_index(batch_op.f('idx_documento_entidade_tipo'), ['tipo'], unique=False)
        batch_op.create_index(batch_op.f('idx_documento_data_vencimento'), ['data_vencimento'], unique=False)
        