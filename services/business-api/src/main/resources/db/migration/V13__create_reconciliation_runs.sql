CREATE TABLE routemind.reconciliation_runs (
    run_id UUID PRIMARY KEY,
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) NOT NULL,
    repair_mode VARCHAR(32) NOT NULL,
    violation_count INTEGER NOT NULL,
    unavailable_count INTEGER NOT NULL,
    report_digest VARCHAR(64) NOT NULL,
    report_json TEXT NOT NULL,
    CONSTRAINT ck_reconciliation_status CHECK (status IN ('HEALTHY', 'DRIFT_DETECTED', 'DEGRADED')),
    CONSTRAINT ck_reconciliation_repair_mode CHECK (repair_mode = 'DETECT_ONLY'),
    CONSTRAINT ck_reconciliation_counts CHECK (violation_count >= 0 AND unavailable_count >= 0),
    CONSTRAINT ck_reconciliation_digest CHECK (report_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_reconciliation_report_size CHECK (length(report_json) <= 262144)
);

CREATE INDEX ix_reconciliation_runs_checked_at
    ON routemind.reconciliation_runs (checked_at DESC);

COMMENT ON TABLE routemind.reconciliation_runs IS
    'Append-only detect-only invariant scan evidence; no implicit repair authority';
