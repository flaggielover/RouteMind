CREATE TABLE routemind.inbox_messages (
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
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    last_error VARCHAR(500),
    CONSTRAINT ck_inbox_status CHECK (status IN ('RECEIVED', 'PROCESSING', 'PROCESSED', 'RETRYABLE', 'DEAD_LETTER')),
    CONSTRAINT ck_inbox_aggregate_version CHECK (aggregate_version > 0),
    CONSTRAINT ck_inbox_attempts CHECK (attempts >= 0),
    CONSTRAINT ck_inbox_trace_id CHECK (trace_id ~ '^[0-9a-f]{32}$')
);

CREATE INDEX ix_inbox_retry ON routemind.inbox_messages (status, next_attempt_at, received_at);

COMMENT ON TABLE routemind.inbox_messages IS
    'Durable event deduplication and processing state owned by business-api';
