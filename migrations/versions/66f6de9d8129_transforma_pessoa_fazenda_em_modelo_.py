# migrations/versions/migrations/versions/66f6de9d8129_transforma_pessoa_fazenda_em_modelo_.py

"""Transforma pessoa_fazenda em modelo intermediário

Revision ID: 66f6de9d8129
Revises: 125c7b02ed09
Create Date: 2025-07-16 22:08:28.830904

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '66f6de9d8129'
down_revision = '125c7b02ed09'
branch_labels = None
depends_on = None

def index_exists(conn, table_name, index_name):
    sql = """
    SELECT COUNT(1)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema=DATABASE() AND table_name=:table_name AND index_name=:index_name
    """
    res = conn.execute(sa.text(sql), {'table_name': table_name, 'index_name': index_name})
    return res.scalar() > 0

def column_exists(conn, table_name, column_name):
    sql = """
    SELECT COUNT(1)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_schema=DATABASE() AND table_name=:table_name AND column_name=:column_name
    """
    res = conn.execute(sa.text(sql), {'table_name': table_name, 'column_name': column_name})
    return res.scalar() > 0

def constraint_exists(conn, table_name, constraint_name):
    sql = """
    SELECT COUNT(1)
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE table_schema=DATABASE() AND table_name=:table_name AND constraint_name=:constraint_name
    """
    res = conn.execute(sa.text(sql), {'table_name': table_name, 'constraint_name': constraint_name})
    return res.scalar() > 0

def upgrade():
    conn = op.get_bind()

    # Remover índices se existirem
    for table, indexes in [
        ('documento', ['idx_documento_data_vencimento', 'idx_documento_tipo']),
        ('endividamento', ['idx_endividamento_banco', 'idx_endividamento_created_at', 'idx_endividamento_data_vencimento']),
        ('historico_notificacao', ['idx_historico_notificacao_data']),
        ('notificacao_endividamento', ['idx_notificacao_endividamento_ativo']),
        ('parcela', ['idx_parcela_data_vencimento', 'idx_parcela_pago']),
        ('pessoa', ['idx_pessoa_cpf_cnpj', 'idx_pessoa_nome'])
    ]:
        for idx in indexes:
            if index_exists(conn, table, idx):
                with op.batch_alter_table(table, schema=None) as batch_op:
                    batch_op.drop_index(idx)

    # ALTERAÇÃO CRÍTICA EM pessoa_fazenda
    # Adiciona colunas se não existirem
    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        # id
        if not column_exists(conn, 'pessoa_fazenda', 'id'):
            batch_op.add_column(sa.Column('id', sa.Integer(), autoincrement=True, nullable=True))
        # tipo_posse
        if not column_exists(conn, 'pessoa_fazenda', 'tipo_posse'):
            batch_op.add_column(sa.Column('tipo_posse', sa.Enum('PROPRIA', 'ARRENDADA', 'COMODATO', 'POSSE', name='tipo_posse_enum'), nullable=False, server_default='PROPRIA'))
        # data_inicio
        if not column_exists(conn, 'pessoa_fazenda', 'data_inicio'):
            batch_op.add_column(sa.Column('data_inicio', sa.Date(), nullable=True))
        # data_fim
        if not column_exists(conn, 'pessoa_fazenda', 'data_fim'):
            batch_op.add_column(sa.Column('data_fim', sa.Date(), nullable=True))
        # drop antigo índice se existir
        if index_exists(conn, 'pessoa_fazenda', 'idx_pessoa_fazenda'):
            batch_op.drop_index('idx_pessoa_fazenda')
        # criar índices novos se não existirem
        if not index_exists(conn, 'pessoa_fazenda', 'idx_pessoa_fazenda_unico'):
            batch_op.create_index('idx_pessoa_fazenda_unico', ['pessoa_id', 'fazenda_id', 'tipo_posse'], unique=True)
        if not index_exists(conn, 'pessoa_fazenda', 'ix_pessoa_fazenda_fazenda_id'):
            batch_op.create_index('ix_pessoa_fazenda_fazenda_id', ['fazenda_id'], unique=False)
        if not index_exists(conn, 'pessoa_fazenda', 'ix_pessoa_fazenda_pessoa_id'):
            batch_op.create_index('ix_pessoa_fazenda_pessoa_id', ['pessoa_id'], unique=False)
        if not index_exists(conn, 'pessoa_fazenda', 'ix_pessoa_fazenda_tipo_posse'):
            batch_op.create_index('ix_pessoa_fazenda_tipo_posse', ['tipo_posse'], unique=False)

    # Preencher 'id' incremental para registros antigos (se id existir e houver linhas sem id)
    if column_exists(conn, 'pessoa_fazenda', 'id'):
        op.execute("SET @rownum := 0")
        op.execute("UPDATE pessoa_fazenda SET id = (@rownum := @rownum + 1) WHERE id IS NULL")
        op.alter_column('pessoa_fazenda', 'id', existing_type=sa.Integer(), nullable=False)

    # Preencher data_inicio para linhas antigas
    if column_exists(conn, 'pessoa_fazenda', 'data_inicio'):
        op.execute("""
            UPDATE pessoa_fazenda SET data_inicio = CURDATE() WHERE data_inicio IS NULL;
        """)
        op.alter_column('pessoa_fazenda', 'data_inicio', existing_type=sa.Date(), nullable=False)

    # Remover PK composta antiga, se existir
    if constraint_exists(conn, 'pessoa_fazenda', 'PRIMARY'):
        op.drop_constraint('PRIMARY', 'pessoa_fazenda', type_='primary')
    # Criar PK nova em 'id', se não houver
    if not constraint_exists(conn, 'pessoa_fazenda', 'pk_pessoa_fazenda'):
        op.create_primary_key('pk_pessoa_fazenda', 'pessoa_fazenda', ['id'])

def downgrade():
    # O downgrade não é idempotente, pois se rodar novamente pode dar erro,
    # mas mantemos o padrão do Alembic e prescrevemos reversão "seca".
    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        batch_op.drop_index('ix_pessoa_fazenda_tipo_posse')
        batch_op.drop_index('ix_pessoa_fazenda_pessoa_id')
        batch_op.drop_index('ix_pessoa_fazenda_fazenda_id')
        batch_op.drop_index('idx_pessoa_fazenda_unico')
        batch_op.create_index('idx_pessoa_fazenda', ['pessoa_id', 'fazenda_id'], unique=False)
        batch_op.drop_column('data_fim')
        batch_op.drop_column('data_inicio')
        batch_op.drop_column('tipo_posse')
        batch_op.drop_column('id')

    with op.batch_alter_table('pessoa', schema=None) as batch_op:
        batch_op.create_index('idx_pessoa_nome', ['nome'], unique=False)
        batch_op.create_index('idx_pessoa_cpf_cnpj', ['cpf_cnpj'], unique=False)

    with op.batch_alter_table('parcela', schema=None) as batch_op:
        batch_op.create_index('idx_parcela_pago', ['pago'], unique=False)
        batch_op.create_index('idx_parcela_endividamento_id', ['endividamento_id'], unique=False)
        batch_op.create_index('idx_parcela_data_vencimento', ['data_vencimento'], unique=False)

    with op.batch_alter_table('notificacao_endividamento', schema=None) as batch_op:
        batch_op.create_index('idx_notificacao_endividamento_ativo', ['ativo'], unique=False)

    with op.batch_alter_table('historico_notificacao', schema=None) as batch_op:
        batch_op.add_column(sa.Column('documento_id', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.add_column(sa.Column('dias_antes', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.add_column(sa.Column('mensagem', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=True))
        batch_op.add_column(sa.Column('destinatarios', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=False))
        batch_op.create_index('idx_historico_notificacao_data', ['data_envio'], unique=False)

    # with op.batch_alter_table('fazenda', schema=None) as batch_op:
    #     batch_op.add_column(sa.Column('tipo_posse', mysql.ENUM('PROPRIA', 'ARRENDADA', 'COMODATO', 'POSSE', collation='utf8mb4_unicode_ci'), nullable=False))
    #     batch_op.create_index('ix_fazenda_tipo_posse', ['tipo_posse'], unique=False)
    #     batch_op.create_index('idx_fazenda_tipo_posse', ['tipo_posse'], unique=False)

    with op.batch_alter_table('endividamento', schema=None) as batch_op:
        batch_op.create_index('idx_endividamento_data_vencimento', ['data_vencimento_final'], unique=False)
        batch_op.create_index('idx_endividamento_created_at', ['created_at'], unique=False)
        batch_op.create_index('idx_endividamento_banco', ['banco'], unique=False)

    with op.batch_alter_table('documento', schema=None) as batch_op:
        batch_op.create_index('idx_documento_tipo', ['tipo'], unique=False)
        batch_op.create_index('idx_documento_data_vencimento', ['data_vencimento'], unique=False)

    op.create_table('historico_notificacao_endividamento',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('endividamento_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('tipo_notificacao', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=20), nullable=False),
    sa.Column('data_envio', mysql.DATETIME(), nullable=True),
    sa.Column('emails_enviados', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=False),
    sa.Column('sucesso', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('erro_mensagem', mysql.TEXT(collation='utf8mb4_unicode_ci'), nullable=True),
    sa.ForeignKeyConstraint(['endividamento_id'], ['endividamento.id'], name=op.f('historico_notificacao_endividamento_ibfk_1')),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )