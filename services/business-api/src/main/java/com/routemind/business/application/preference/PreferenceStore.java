package com.routemind.business.application.preference;

import java.time.Instant;
import java.util.Optional;

public interface PreferenceStore {

	Optional<PreferenceDocument> find(PreferenceIdentity identity, PreferenceNamespace namespace);

	PreferenceDocument write(PreferenceIdentity identity, PreferenceNamespace namespace, String canonicalValue,
			long expectedVersion, String idempotencyKey, String requestDigest, String valueDigest, Instant changedAt);
}
