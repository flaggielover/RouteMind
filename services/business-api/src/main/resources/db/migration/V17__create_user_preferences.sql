CREATE TABLE routemind.user_preferences (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    principal_id VARCHAR(200) NOT NULL,
    namespace VARCHAR(32) NOT NULL,
    owner_role VARCHAR(16) NOT NULL,
    value_json VARCHAR(4096) NOT NULL,
    version BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_user_preferences_scope UNIQUE (tenant_id, principal_id, namespace),
    CONSTRAINT ck_user_preferences_namespace CHECK (
        namespace IN ('accessibility', 'locale', 'notifications', 'quiet_hours')
    ),
    CONSTRAINT ck_user_preferences_role CHECK (
        owner_role IN ('customer', 'courier', 'merchant', 'analyst', 'operator')
    ),
    CONSTRAINT ck_user_preferences_version CHECK (version > 0)
);

CREATE TABLE routemind.user_preference_commands (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    principal_id VARCHAR(200) NOT NULL,
    operation VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_digest VARCHAR(64) NOT NULL,
    namespace VARCHAR(32) NOT NULL,
    owner_role VARCHAR(16) NOT NULL,
    response_value_json VARCHAR(4096) NOT NULL,
    response_version BIGINT NOT NULL,
    response_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    response_updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_user_preference_commands_scope UNIQUE (
        tenant_id, principal_id, operation, idempotency_key
    )
);

CREATE TABLE routemind.user_preference_audits (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    principal_id VARCHAR(200) NOT NULL,
    namespace VARCHAR(32) NOT NULL,
    owner_role VARCHAR(16) NOT NULL,
    operation VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    previous_version BIGINT NOT NULL,
    resulting_version BIGINT NOT NULL,
    value_digest VARCHAR(64) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_user_preference_audit_versions CHECK (
        previous_version >= 0 AND resulting_version = previous_version + 1
    )
);

CREATE INDEX ix_user_preferences_tenant_principal
    ON routemind.user_preferences (tenant_id, principal_id);
CREATE INDEX ix_user_preference_commands_tenant_created
    ON routemind.user_preference_commands (tenant_id, created_at);
CREATE INDEX ix_user_preference_audits_scope
    ON routemind.user_preference_audits (tenant_id, principal_id, namespace, changed_at);
