CREATE TABLE routemind.order_command_idempotency (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    request_hash VARCHAR(64) NOT NULL,
    operation VARCHAR(32) NOT NULL,
    order_id UUID NOT NULL,
    response_status VARCHAR(16) NOT NULL,
    response_version BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_order_command_idempotency_hash CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_order_command_idempotency_version CHECK (response_version >= 0)
);

COMMENT ON TABLE routemind.order_command_idempotency IS
    'Durable command idempotency records owned by business-api';
