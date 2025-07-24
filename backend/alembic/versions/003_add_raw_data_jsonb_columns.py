"""add raw_data jsonb columns and recording table

Revision ID: 003
Revises: 002
Create Date: 2025-07-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add raw_data column to calls table
    op.add_column('calls', sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True))
    
    # Add raw_data column to transcriptions table
    op.add_column('transcriptions', sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True))
    
    # Create recordings table
    op.create_table('recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recording_id', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('format', sa.String(length=10), nullable=True),
        sa.Column('stereo', sa.Boolean(), nullable=True, default=False),
        sa.Column('direction', sa.String(length=20), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recording_id')
    )
    op.create_index(op.f('ix_recordings_call_id'), 'recordings', ['call_id'], unique=False)


def downgrade():
    # Drop recordings table
    op.drop_index(op.f('ix_recordings_call_id'), table_name='recordings')
    op.drop_table('recordings')
    
    # Remove raw_data columns
    op.drop_column('transcriptions', 'raw_data')
    op.drop_column('calls', 'raw_data')