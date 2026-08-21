package com.routemind.business.domain.party;

import java.time.Instant;
import java.util.Objects;

public record AuditMetadata(Instant createdAt, Instant updatedAt) {

	public AuditMetadata {
		Objects.requireNonNull(createdAt, "createdAt must not be null");
		Objects.requireNonNull(updatedAt, "updatedAt must not be null");
		if (updatedAt.isBefore(createdAt)) {
			throw new IllegalArgumentException("updatedAt must not be before createdAt");
		}
	}

	public static AuditMetadata initial(Instant now) {
		return new AuditMetadata(now, now);
	}

	public AuditMetadata touch(Instant now) {
		Objects.requireNonNull(now, "now must not be null");
		if (!now.isAfter(updatedAt)) {
			throw new IllegalArgumentException("updatedAt must advance");
		}
		return new AuditMetadata(createdAt, now);
	}
}
