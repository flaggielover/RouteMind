ALTER TABLE routemind.orders DROP CONSTRAINT ck_orders_status;
ALTER TABLE routemind.orders ADD CONSTRAINT ck_orders_status CHECK (
    status IN ('CREATED', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP', 'DELIVERED', 'CANCELLED')
);

CREATE TABLE routemind.courier_shifts (
    courier_id UUID PRIMARY KEY,
    status VARCHAR(16) NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_courier_shift_status CHECK (status IN ('OFFLINE', 'ONLINE')),
    CONSTRAINT ck_courier_shift_version CHECK (version >= 0)
);

CREATE TABLE routemind.courier_command_idempotency (
    idempotency_key VARCHAR(128) PRIMARY KEY,
    request_hash VARCHAR(64) NOT NULL,
    operation VARCHAR(32) NOT NULL,
    courier_id UUID NOT NULL,
    response_status VARCHAR(16) NOT NULL,
    response_version BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_courier_command_hash CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_courier_command_version CHECK (response_version >= 0)
);

COMMENT ON TABLE routemind.courier_shifts IS 'Durable courier availability and shift state owned by business-api';
COMMENT ON TABLE routemind.courier_command_idempotency IS 'Durable courier command deduplication records owned by business-api';
