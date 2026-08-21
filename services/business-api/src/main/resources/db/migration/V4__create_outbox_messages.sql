CREATE TABLE routemind.outbox_messages (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(120) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    producer VARCHAR(120) NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_version BIGINT NOT NULL,
    correlation_id UUID NOT NULL,
    causation_id UUID,
    trace_id VARCHAR(32) NOT NULL,
    payload_json TEXT NOT NULL,
    status VARCHAR(16) NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    last_error VARCHAR(500),
    CONSTRAINT ck_outbox_status CHECK (status IN ('PENDING', 'IN_FLIGHT', 'PUBLISHED', 'RETRYABLE')),
    CONSTRAINT ck_outbox_aggregate_version CHECK (aggregate_version > 0),
    CONSTRAINT ck_outbox_attempts CHECK (attempts >= 0),
    CONSTRAINT ck_outbox_trace_id CHECK (trace_id ~ '^[0-9a-f]{32}$')
);

CREATE INDEX ix_outbox_due ON routemind.outbox_messages (status, next_attempt_at, created_at);

COMMENT ON TABLE routemind.outbox_messages IS
    'Durable event publication queue owned by business-api';
