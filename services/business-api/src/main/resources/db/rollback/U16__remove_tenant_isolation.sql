-- PRECONDITION: every tenant_id is the legacy tenant and every physical key
-- still equals its logical key. After non-legacy traffic, restore a pre-V16
-- snapshot instead; collapsing tenant namespaces is intentionally unsupported.
DROP INDEX routemind.ix_parties_tenant;
DROP INDEX routemind.ix_orders_tenant;
DROP INDEX routemind.ix_order_transitions_tenant;
DROP INDEX routemind.ix_outbox_tenant_due;
DROP INDEX routemind.ix_inbox_tenant_retry;
DROP INDEX routemind.ix_courier_locations_tenant;
DROP INDEX routemind.uk_order_command_tenant_logical_key;
DROP INDEX routemind.ix_courier_shifts_tenant;
DROP INDEX routemind.uk_courier_command_tenant_logical_key;
DROP INDEX routemind.uk_dispatch_audit_tenant_logical_key;
DROP INDEX routemind.ix_dispatch_audit_tenant_order;
DROP INDEX routemind.ix_dispatch_leases_tenant_courier;
DROP INDEX routemind.ix_dispatch_lease_events_tenant;
DROP INDEX routemind.uk_dispatch_ledger_tenant_decision;
DROP INDEX routemind.uk_dispatch_ledger_tenant_idempotency;
DROP INDEX routemind.ix_reconciliation_runs_tenant;
DROP INDEX routemind.ix_courier_history_tenant_lookup;

ALTER TABLE routemind.parties DROP CONSTRAINT uk_parties_tenant_type_external_reference;
ALTER TABLE routemind.parties ADD CONSTRAINT uk_parties_type_external_reference
    UNIQUE (party_type, external_reference);
ALTER TABLE routemind.order_transitions DROP CONSTRAINT uk_order_transitions_tenant_order_sequence;
ALTER TABLE routemind.order_transitions ADD CONSTRAINT uk_order_transitions_order_sequence
    UNIQUE (order_id, sequence_number);
ALTER TABLE routemind.courier_location_history DROP CONSTRAINT uk_courier_location_history_tenant_sequence;
ALTER TABLE routemind.courier_location_history ADD CONSTRAINT uk_courier_location_history_sequence
    UNIQUE (courier_id, location_sequence);

ALTER TABLE routemind.order_command_idempotency DROP COLUMN logical_key;
ALTER TABLE routemind.courier_command_idempotency DROP COLUMN logical_key;
ALTER TABLE routemind.dispatch_assignment_audits DROP COLUMN logical_key;
ALTER TABLE routemind.dispatch_decision_ledger DROP COLUMN logical_decision_id;
ALTER TABLE routemind.dispatch_decision_ledger DROP COLUMN logical_idempotency_key;

ALTER TABLE routemind.parties DROP COLUMN tenant_id;
ALTER TABLE routemind.orders DROP COLUMN tenant_id;
ALTER TABLE routemind.order_transitions DROP COLUMN tenant_id;
ALTER TABLE routemind.outbox_messages DROP COLUMN tenant_id;
ALTER TABLE routemind.inbox_messages DROP COLUMN tenant_id;
ALTER TABLE routemind.courier_locations DROP COLUMN tenant_id;
ALTER TABLE routemind.order_command_idempotency DROP COLUMN tenant_id;
ALTER TABLE routemind.courier_shifts DROP COLUMN tenant_id;
ALTER TABLE routemind.courier_command_idempotency DROP COLUMN tenant_id;
ALTER TABLE routemind.dispatch_assignment_audits DROP COLUMN tenant_id;
ALTER TABLE routemind.dispatch_assignment_leases DROP COLUMN tenant_id;
ALTER TABLE routemind.dispatch_assignment_lease_events DROP COLUMN tenant_id;
ALTER TABLE routemind.dispatch_decision_ledger DROP COLUMN tenant_id;
ALTER TABLE routemind.reconciliation_runs DROP COLUMN tenant_id;
ALTER TABLE routemind.courier_location_history DROP COLUMN tenant_id;
