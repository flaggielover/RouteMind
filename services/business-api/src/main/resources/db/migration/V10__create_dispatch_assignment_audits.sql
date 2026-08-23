CREATE TABLE routemind.dispatch_assignment_audits (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    request_hash VARCHAR(64) NOT NULL,
    request_id VARCHAR(128) NOT NULL,
    order_id UUID NOT NULL REFERENCES routemind.orders(id) ON DELETE CASCADE,
    courier_id UUID NOT NULL,
    contract_version VARCHAR(16) NOT NULL,
    strategy VARCHAR(64) NOT NULL,
    strategy_version VARCHAR(64) NOT NULL,
    input_digest VARCHAR(64) NOT NULL,
    output_digest VARCHAR(64) NOT NULL,
    trace_id VARCHAR(32) NOT NULL,
    fallback_used BOOLEAN NOT NULL,
    fallback_reason VARCHAR(256),
    applied_order_version BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_dispatch_audit_hash CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_audit_input_digest CHECK (input_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_audit_output_digest CHECK (output_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_audit_trace CHECK (trace_id ~ '^[0-9a-f]{32}$'),
    CONSTRAINT ck_dispatch_audit_contract CHECK (contract_version = 'v1'),
    CONSTRAINT ck_dispatch_audit_version CHECK (applied_order_version > 0),
    CONSTRAINT ck_dispatch_audit_fallback_reason CHECK (fallback_used OR fallback_reason IS NULL OR length(trim(fallback_reason)) > 0)
);

CREATE INDEX ix_dispatch_assignment_audits_order
    ON routemind.dispatch_assignment_audits (order_id, created_at);

COMMENT ON TABLE routemind.dispatch_assignment_audits IS
    'Durable versioned dispatch decisions applied to order authority';
