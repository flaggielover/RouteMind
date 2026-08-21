package com.routemind.business.domain.party;

import java.time.Instant;
import java.util.Objects;

public record Party(PartyIdentity identity, PartyStatus status, AuditMetadata auditMetadata) {

	public Party {
		Objects.requireNonNull(identity, "identity must not be null");
		Objects.requireNonNull(status, "status must not be null");
		Objects.requireNonNull(auditMetadata, "auditMetadata must not be null");
	}

	public static Party active(PartyIdentity identity, Instant now) {
		return new Party(identity, PartyStatus.ACTIVE, AuditMetadata.initial(now));
	}

	public Party rename(String displayName, Instant now) {
		return new Party(identity.withDisplayName(displayName), status, auditMetadata.touch(now));
	}

	public PartyId id() {
		return identity.id();
	}
}
