"""Add Remote Boulder Tables and Columns

Revision ID: add_remote_boulder_tables
Revises:
Create Date: 2023-06-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_remote_boulder_tables'
down_revision = None  # Update this to match your previous migration
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create remote_boulder_bonus table
    op.create_table(
        'remote_boulder_bonus',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('competition_id', postgresql.UUID(), nullable=False),
        sa.Column('boulder_id', postgresql.UUID(), nullable=False),
        sa.Column('bonus_factor', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ['competition_id'],
            ['competitions.id'],
        ),
        sa.ForeignKeyConstraint(
            ['boulder_id'],
            ['boulders.id'],
        ),
        sa.PrimaryKeyConstraint('id'))

    # 2. Add remote_boulder_bonus column to marathon_rankings table
    op.add_column(
        'marathon_rankings',
        sa.Column('remote_boulder_bonus',
                  sa.Float(),
                  server_default='0',
                  nullable=False))

    # 3. Add remote_boulder_bonus column to marathon_detailed_results table
    op.add_column(
        'marathon_detailed_results',
        sa.Column('remote_boulder_bonus',
                  sa.Float(),
                  server_default='0',
                  nullable=False))


def downgrade():
    # 1. Drop remote_boulder_bonus column from marathon_detailed_results table
    op.drop_column('marathon_detailed_results', 'remote_boulder_bonus')

    # 2. Drop remote_boulder_bonus column from marathon_rankings table
    op.drop_column('marathon_rankings', 'remote_boulder_bonus')

    # 3. Drop remote_boulder_bonus table
    op.drop_table('remote_boulder_bonus')
