"""Initial database schema for Bank Statement Analyzer.

Revision ID: 001_initial
Revises: 
Create Date: 2025-10-26

This migration creates the core tables:
- analyses: Stores salary analysis results
- audit_logs: Tracks API operations for security and debugging
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema with analyses and audit_logs tables."""
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('detected_salary', sa.Numeric(15, 2)),
        sa.Column('confidence', sa.String(20), nullable=False),
        sa.Column('transactions_analyzed', sa.Integer, nullable=False),
        sa.Column('credit_transactions', sa.Integer),
        sa.Column('debit_transactions', sa.Integer),
        sa.Column('clusters_found', sa.Integer),
        sa.Column('top_candidates_count', sa.Integer),
        sa.Column('expected_gross', sa.Numeric(15, 2)),
        sa.Column('matches_expected', sa.Boolean),
        sa.Column('difference', sa.Numeric(15, 2)),
        sa.Column('difference_percentage', sa.Numeric(5, 2)),
        sa.Column('employer', sa.String(255)),
        sa.Column('pvd_rate', sa.Numeric(5, 4)),
        sa.Column('extra_deductions', sa.Numeric(15, 2)),
        sa.Column('pdf_filename', sa.String(255)),
        sa.Column('pages_processed', sa.Integer),
        sa.Column('masked_items', sa.Integer),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("confidence IN ('high', 'medium', 'low')", name='analyses_confidence_check')
    )
    
    # Create indexes for analyses table
    op.create_index('idx_analyses_user_id', 'analyses', ['user_id'])
    op.create_index('idx_analyses_confidence', 'analyses', ['confidence'])
    op.create_index('idx_analyses_detected_salary', 'analyses', ['detected_salary'])
    op.create_index('idx_analyses_created_at', 'analyses', ['created_at'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text),
        sa.Column('error_type', sa.String(100)),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text),
        sa.Column('processing_time_ms', sa.Integer),
        sa.Column('request_payload', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('success', 'failed', 'pending')", name='audit_logs_status_check')
    )
    
    # Create indexes for audit_logs table
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_analysis_id', 'audit_logs', ['analysis_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_status', 'audit_logs', ['status'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # Add table comments
    op.execute("""
        COMMENT ON TABLE analyses IS 'Salary analysis results with embedded statistics and metadata'
    """)
    op.execute("""
        COMMENT ON TABLE audit_logs IS 'Audit trail for all API operations'
    """)
    
    # Add column comments
    op.execute("""
        COMMENT ON COLUMN analyses.metadata IS 'Additional analysis data in JSON format (top candidates, statistics)'
    """)
    op.execute("""
        COMMENT ON COLUMN analyses.masked_items IS 'Number of PDPA-masked items'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.processing_time_ms IS 'API request processing time in milliseconds'
    """)
    op.execute("""
        COMMENT ON COLUMN audit_logs.request_payload IS 'Request parameters (excluding sensitive data)'
    """)


def downgrade() -> None:
    """Drop all tables and extensions."""
    
    # Drop indexes first
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_logs_status', table_name='audit_logs')
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_analysis_id', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_id', table_name='audit_logs')
    
    op.drop_index('idx_analyses_created_at', table_name='analyses')
    op.drop_index('idx_analyses_detected_salary', table_name='analyses')
    op.drop_index('idx_analyses_confidence', table_name='analyses')
    op.drop_index('idx_analyses_user_id', table_name='analyses')
    
    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('analyses')
    
    # Drop extension (optional - might be used by other databases)
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
