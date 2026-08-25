package com.routemind.business.application.preference;

import java.time.Instant;

public record PreferenceDocument(PreferenceNamespace namespace, String ownerRole, String valueJson, long version,
		boolean persisted, boolean replayed, Instant createdAt, Instant updatedAt) {
}
