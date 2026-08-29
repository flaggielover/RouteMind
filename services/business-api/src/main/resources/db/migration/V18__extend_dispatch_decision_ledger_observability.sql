ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_schema_version VARCHAR(128) NOT NULL DEFAULT 'routemind-policy-observation-v1';
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_run_id VARCHAR(256);
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_scenario_id VARCHAR(256);
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_simulation_tick BIGINT;
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_decision_reason VARCHAR(128) NOT NULL DEFAULT 'dispatch_assignment';
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_policy_selection_mode VARCHAR(128) NOT NULL DEFAULT 'java_command';
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_fallback_state VARCHAR(64) NOT NULL DEFAULT 'NONE';
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_configuration_digest VARCHAR(64);
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_deterministic_seed BIGINT;
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_state_snapshot_reference VARCHAR(256);
ALTER TABLE routemind.dispatch_decision_ledger ADD COLUMN observation_provenance_reference VARCHAR(256);

ALTER TABLE routemind.dispatch_decision_ledger ADD CONSTRAINT ck_dispatch_ledger_observation_schema
    CHECK (observation_schema_version = 'routemind-policy-observation-v1');
ALTER TABLE routemind.dispatch_decision_ledger ADD CONSTRAINT ck_dispatch_ledger_observation_config_digest
    CHECK (observation_configuration_digest IS NULL OR observation_configuration_digest ~ '^[0-9a-f]{64}$');
ALTER TABLE routemind.dispatch_decision_ledger ADD CONSTRAINT ck_dispatch_ledger_observation_tick
    CHECK (observation_simulation_tick IS NULL OR observation_simulation_tick >= 0);
ALTER TABLE routemind.dispatch_decision_ledger ADD CONSTRAINT ck_dispatch_ledger_observation_seed
    CHECK (observation_deterministic_seed IS NULL OR observation_deterministic_seed >= 0);
