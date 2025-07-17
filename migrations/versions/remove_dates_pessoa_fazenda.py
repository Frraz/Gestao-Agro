"""Remove date fields from pessoa_fazenda table

Revision ID: remove_dates_pessoa_fazenda
Revises: 66f6de9d8129
Create Date: 2025-01-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_dates_pessoa_fazenda'
down_revision = '66f6de9d8129'
branch_labels = None
depends_on = None


def column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    sql = """
    SELECT COUNT(1)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_schema=DATABASE() AND table_name=:table_name AND column_name=:column_name
    """
    res = conn.execute(sa.text(sql), {'table_name': table_name, 'column_name': column_name})
    return res.scalar() > 0


def index_exists(conn, table_name, index_name):
    """Check if an index exists in a table"""
    sql = """
    SELECT COUNT(1)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE table_schema=DATABASE() AND table_name=:table_name AND index_name=:index_name
    """
    res = conn.execute(sa.text(sql), {'table_name': table_name, 'index_name': index_name})
    return res.scalar() > 0


def upgrade():
    """Remove date fields from pessoa_fazenda table and update unique constraint"""
    conn = op.get_bind()

    # First, drop the unique constraint if it exists
    if index_exists(conn, 'pessoa_fazenda', 'idx_pessoa_fazenda_unico'):
        op.drop_index('idx_pessoa_fazenda_unico', table_name='pessoa_fazenda')

    # Remove date columns if they exist
    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        if column_exists(conn, 'pessoa_fazenda', 'data_inicio'):
            batch_op.drop_column('data_inicio')
        if column_exists(conn, 'pessoa_fazenda', 'data_fim'):
            batch_op.drop_column('data_fim')
        
        # Create new non-unique index to allow multiple relationships
        if not index_exists(conn, 'pessoa_fazenda', 'idx_pessoa_fazenda'):
            batch_op.create_index('idx_pessoa_fazenda', ['pessoa_id', 'fazenda_id', 'tipo_posse'])


def downgrade():
    """Add date fields back to pessoa_fazenda table"""
    conn = op.get_bind()

    # Drop the non-unique index
    if index_exists(conn, 'pessoa_fazenda', 'idx_pessoa_fazenda'):
        op.drop_index('idx_pessoa_fazenda', table_name='pessoa_fazenda')

    # Add date columns back
    with op.batch_alter_table('pessoa_fazenda', schema=None) as batch_op:
        if not column_exists(conn, 'pessoa_fazenda', 'data_inicio'):
            batch_op.add_column(sa.Column('data_inicio', sa.Date(), nullable=True))
        if not column_exists(conn, 'pessoa_fazenda', 'data_fim'):
            batch_op.add_column(sa.Column('data_fim', sa.Date(), nullable=True))
        
        # Recreate the unique constraint
        if not index_exists(conn, 'pessoa_fazenda', 'idx_pessoa_fazenda_unico'):
            batch_op.create_index('idx_pessoa_fazenda_unico', ['pessoa_id', 'fazenda_id', 'tipo_posse'], unique=True)