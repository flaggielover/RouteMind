-- Legacy rows are assigned to the stable compatibility tenant. New request paths
-- always provide a verified tenant before reaching durable adapters.
ALTER TABLE routemind.parties ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.orders ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.order_transitions ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.outbox_messages ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.inbox_messages ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.courier_locations ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.order_command_idempotency ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.courier_shifts ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.courier_command_idempotency ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.dispatch_assignment_audits ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.dispatch_assignment_leases ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.dispatch_assignment_lease_events ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.reconciliation_runs ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;
ALTER TABLE routemind.courier_location_history ADD COLUMN tenant_id UUID DEFAULT '00000000-0000-0000-0000-000000000001' NOT NULL;

-- Logical keys retain the API-visible idempotency identity while non-legacy
-- tenants use a tenant-derived physical primary key.
ALTER TABLE routemind.order_command_idempotency ADD COLUMN logical_key VARCHAR(128);
UPDATE routemind.order_command_idempotency SET logical_key = idempotency_key;
ALTER TABLE routemind.order_command_idempotency ALTER COLUMN logical_key SET NOT NULL;

ALTER TABLE routemind.courier_command_idempotency ADD COLUMN logical_key VARCHAR(128);
UPDATE routemind.courier_command_idempotency SET logical_key = idempotency_key;
ALTER TABLE routemind.courier_command_idempotency ALTER COLUMN logical_key SET NOT NULL;

ALTER TABLE routemind.dispatch_assignment_audits ADD COLUMN logical_key VARCHAR(128);
UPDATE routemind.dispatch_assignment_audits SET logical_key = idempotency_key;
ALTER TABLE routemind.dispatch_assignment_audits ALTER COLUMN logical_key SET NOT NULL;

ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN logical_decision_id VARCHAR(128);
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN logical_idempotency_key VARCHAR(128);
UPDATE routemind.dispatch_decision_ledger
SET logical_decision_id = decision_id, logical_idempotency_key = idempotency_key;
ALTER TABLE routemind.dispatch_decision_ledger ALTER COLUMN logical_decision_id SET NOT NULL;
ALTER TABLE routemind.dispatch_decision_ledger ALTER COLUMN logical_idempotency_key SET NOT NULL;

ALTER TABLE routemind.parties DROP CONSTRAINT uk_parties_type_external_reference;
ALTER TABLE routemind.parties ADD CONSTRAINT uk_parties_tenant_type_external_reference
    UNIQUE (tenant_id, party_type, external_reference);

ALTER TABLE routemind.order_transitions DROP CONSTRAINT uk_order_transitions_order_sequence;
ALTER TABLE routemind.order_transitions ADD CONSTRAINT uk_order_transitions_tenant_order_sequence
    UNIQUE (tenant_id, order_id, sequence_number);

ALTER TABLE routemind.courier_location_history DROP CONSTRAINT uk_courier_location_history_sequence;
ALTER TABLE routemind.courier_location_history ADD CONSTRAINT uk_courier_location_history_tenant_sequence
    UNIQUE (tenant_id, courier_id, location_sequence);

CREATE INDEX ix_parties_tenant ON routemind.parties (tenant_id, id);
CREATE INDEX ix_orders_tenant ON routemind.orders (tenant_id, id);
CREATE INDEX ix_order_transitions_tenant ON routemind.order_transitions (tenant_id, order_id, sequence_number);
CREATE INDEX ix_outbox_tenant_due ON routemind.outbox_messages (tenant_id, status, next_attempt_at, created_at);
CREATE INDEX ix_inbox_tenant_retry ON routemind.inbox_messages (tenant_id, status, next_attempt_at, received_at);
CREATE INDEX ix_courier_locations_tenant ON routemind.courier_locations (tenant_id, courier_id);
CREATE UNIQUE INDEX uk_order_command_tenant_logical_key
    ON routemind.order_command_idempotency (tenant_id, logical_key);
CREATE INDEX ix_courier_shifts_tenant ON routemind.courier_shifts (tenant_id, courier_id);
CREATE UNIQUE INDEX uk_courier_command_tenant_logical_key
    ON routemind.courier_command_idempotency (tenant_id, logical_key);
CREATE UNIQUE INDEX uk_dispatch_audit_tenant_logical_key
    ON routemind.dispatch_assignment_audits (tenant_id, logical_key);
CREATE INDEX ix_dispatch_audit_tenant_order
    ON routemind.dispatch_assignment_audits (tenant_id, order_id, created_at);
CREATE INDEX ix_dispatch_leases_tenant_courier
    ON routemind.dispatch_assignment_leases (tenant_id, courier_id);
CREATE INDEX ix_dispatch_lease_events_tenant
    ON routemind.dispatch_assignment_lease_events (tenant_id, courier_id, occurred_at);
CREATE UNIQUE INDEX uk_dispatch_ledger_tenant_decision
    ON routemind.dispatch_decision_ledger (tenant_id, logical_decision_id);
CREATE UNIQUE INDEX uk_dispatch_ledger_tenant_idempotency
    ON routemind.dispatch_decision_ledger (tenant_id, logical_idempotency_key);
CREATE INDEX ix_reconciliation_runs_tenant
    ON routemind.reconciliation_runs (tenant_id, checked_at DESC);
CREATE INDEX ix_courier_history_tenant_lookup
    ON routemind.courier_location_history (tenant_id, courier_id, location_sequence DESC);
