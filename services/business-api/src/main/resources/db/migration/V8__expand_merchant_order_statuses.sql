ALTER TABLE routemind.orders DROP CONSTRAINT ck_orders_status;
ALTER TABLE routemind.orders ADD CONSTRAINT ck_orders_status CHECK (
    status IN ('CREATED', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'ASSIGNED', 'PICKED_UP', 'DELIVERED', 'CANCELLED')
);
