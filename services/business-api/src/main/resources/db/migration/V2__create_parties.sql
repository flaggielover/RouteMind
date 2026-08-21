CREATE TABLE routemind.parties (
    id UUID PRIMARY KEY,
    party_type VARCHAR(16) NOT NULL,
    external_reference VARCHAR(64) NOT NULL,
    display_name VARCHAR(120) NOT NULL,
    status VARCHAR(16) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT uk_parties_type_external_reference
        UNIQUE (party_type, external_reference),
    CONSTRAINT ck_parties_type
        CHECK (party_type IN ('CUSTOMER', 'MERCHANT', 'COURIER')),
    CONSTRAINT ck_parties_status
        CHECK (status IN ('ACTIVE', 'SUSPENDED')),
    CONSTRAINT ck_parties_external_reference
        CHECK (CHAR_LENGTH(external_reference) BETWEEN 1 AND 64
            AND external_reference = TRIM(external_reference)),
    CONSTRAINT ck_parties_display_name
        CHECK (CHAR_LENGTH(display_name) BETWEEN 1 AND 120
            AND display_name = TRIM(display_name)),
    CONSTRAINT ck_parties_audit_order
        CHECK (updated_at >= created_at)
);

COMMENT ON TABLE routemind.parties IS
    'Authoritative customer, merchant, and courier identities';
