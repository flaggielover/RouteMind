ALTER TABLE routemind.orders DROP CONSTRAINT ck_orders_status;

ALTER TABLE routemind.orders ALTER COLUMN status TYPE VARCHAR(32);
ALTER TABLE routemind.order_transitions ALTER COLUMN from_status TYPE VARCHAR(32);
ALTER TABLE routemind.order_transitions ALTER COLUMN to_status TYPE VARCHAR(32);
ALTER TABLE routemind.order_command_idempotency ALTER COLUMN response_status TYPE VARCHAR(32);

ALTER TABLE routemind.orders ADD CONSTRAINT ck_orders_status CHECK (
    status IN (
        'CREATED', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'ASSIGNED',
        'ACCEPTED', 'ARRIVED', 'PICKED_UP', 'DELIVERED',
        'ASSIGNMENT_TIMED_OUT', 'ASSIGNMENT_REJECTED', 'REASSIGNMENT_PENDING',
        'COMPENSATING', 'COMPENSATED', 'CANCELLED'
    )
);
