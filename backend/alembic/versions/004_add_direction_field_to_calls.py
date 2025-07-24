"""Add direction field to calls table

Revision ID: 004
Revises: 003
Create Date: 2025-01-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add direction column to calls table
    op.add_column('calls', sa.Column('direction', sa.String(20), nullable=True, server_default='outbound'))
    
    # Update existing rows to have 'outbound' as default
    op.execute("UPDATE calls SET direction = 'outbound' WHERE direction IS NULL")
    
    # Make column non-nullable after setting defaults
    op.alter_column('calls', 'direction',
                    existing_type=sa.String(20),
                    nullable=False)


def downgrade() -> None:
    # Remove direction column
    op.drop_column('calls', 'direction')