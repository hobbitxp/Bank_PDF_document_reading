-- Bank Statement Analyzer Database Schema
-- Version: 1.0.0
-- Created: 2025-10-25

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Analyses table
-- Stores salary analysis results with embedded metadata
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    detected_salary DECIMAL(15, 2),
    confidence VARCHAR(20) NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    transactions_analyzed INTEGER NOT NULL,
    credit_transactions INTEGER,
    debit_transactions INTEGER,
    clusters_found INTEGER,
    top_candidates_count INTEGER,
    expected_gross DECIMAL(15, 2),
    matches_expected BOOLEAN,
    difference DECIMAL(15, 2),
    difference_percentage DECIMAL(5, 2),
    employer VARCHAR(255),
    pvd_rate DECIMAL(5, 4),
    extra_deductions DECIMAL(15, 2),
    pdf_filename VARCHAR(255),
    pages_processed INTEGER,
    masked_items INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_confidence ON analyses(confidence);
CREATE INDEX idx_analyses_detected_salary ON analyses(detected_salary);
CREATE INDEX idx_analyses_created_at ON analyses(created_at);

-- Audit logs table
-- Tracks all API operations for security and debugging
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('success', 'failed', 'pending')),
    error_message TEXT,
    error_type VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    processing_time_ms INTEGER,
    request_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_analysis_id ON audit_logs(analysis_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_status ON audit_logs(status);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Comments for documentation
COMMENT ON TABLE analyses IS 'Salary analysis results with embedded statistics and metadata';
COMMENT ON TABLE audit_logs IS 'Audit trail for all API operations';

COMMENT ON COLUMN analyses.metadata IS 'Additional analysis data in JSON format (top candidates, statistics)';
COMMENT ON COLUMN analyses.masked_items IS 'Number of PDPA-masked items';
COMMENT ON COLUMN audit_logs.processing_time_ms IS 'API request processing time in milliseconds';
COMMENT ON COLUMN audit_logs.request_payload IS 'Request parameters (excluding sensitive data)';
