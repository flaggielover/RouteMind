CREATE TABLE routemind.dispatch_decision_ledger (
    decision_id VARCHAR(128) PRIMARY KEY,
    request_id VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES routemind.orders(id) ON DELETE CASCADE,
    courier_id UUID NOT NULL,
    strategy VARCHAR(64) NOT NULL,
    strategy_version VARCHAR(64) NOT NULL,
    reference_data_id VARCHAR(256) NOT NULL,
    clock_domain VARCHAR(16) NOT NULL,
    input_digest VARCHAR(64) NOT NULL,
    output_digest VARCHAR(64) NOT NULL,
    input_snapshot_digest VARCHAR(64) NOT NULL,
    output_snapshot_digest VARCHAR(64) NOT NULL,
    input_snapshot_json TEXT NOT NULL,
    output_snapshot_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_dispatch_ledger_clock CHECK (clock_domain = 'WALL'),
    CONSTRAINT ck_dispatch_ledger_input_digest CHECK (input_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_ledger_output_digest CHECK (output_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_ledger_input_snapshot_digest CHECK (input_snapshot_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_ledger_output_snapshot_digest CHECK (output_snapshot_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_dispatch_ledger_input_snapshot_size CHECK (length(input_snapshot_json) <= 64000),
    CONSTRAINT ck_dispatch_ledger_output_snapshot_size CHECK (length(output_snapshot_json) <= 64000)
);

CREATE INDEX ix_dispatch_decision_ledger_order
    ON routemind.dispatch_decision_ledger (order_id, created_at);

COMMENT ON TABLE routemind.dispatch_decision_ledger IS
    'Durable dispatch decision provenance with bounded content-addressed snapshots; Java-owned authority';
