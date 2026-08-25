package com.routemind.business.application.preference;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.HexFormat;
import java.util.Objects;
import java.util.regex.Pattern;
import org.springframework.stereotype.Service;

@Service
public final class UserPreferenceService {

	private static final Pattern IDEMPOTENCY_KEY = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}");
	private final PreferenceStore store;
	private final PreferencePayloadPolicy policy;
	private final Clock clock;

	public UserPreferenceService(PreferenceStore store, PreferencePayloadPolicy policy, Clock clock) {
		this.store = store;
		this.policy = policy;
		this.clock = clock;
	}

	public PreferenceDocument read(PreferenceIdentity identity, PreferenceNamespace namespace) {
		authorize(identity, namespace);
		return store.find(identity, namespace).orElseGet(() -> new PreferenceDocument(namespace, identity.role(),
				policy.defaults(namespace), 0, false, false, null, null));
	}

	public PreferenceDocument write(PreferenceIdentity identity, PreferenceNamespace namespace, JsonNode value,
			long expectedVersion, String idempotencyKey) {
		authorize(identity, namespace);
		if (expectedVersion < 0) throw new IllegalArgumentException("expected_version_invalid");
		if (idempotencyKey == null || !IDEMPOTENCY_KEY.matcher(idempotencyKey).matches()) {
			throw new IllegalArgumentException("idempotency_key_invalid");
		}
		String canonicalValue = policy.canonicalize(namespace, value);
		String requestDigest = digest(namespace.id() + "|" + expectedVersion + "|" + canonicalValue);
		return store.write(identity, namespace, canonicalValue, expectedVersion, idempotencyKey, requestDigest,
				digest(canonicalValue), clock.instant());
	}

	private static void authorize(PreferenceIdentity identity, PreferenceNamespace namespace) {
		Objects.requireNonNull(identity, "identity");
		Objects.requireNonNull(namespace, "namespace");
		if (!namespace.ownedBy(identity.role())) throw new PreferenceAccessDeniedException();
	}

	private static String digest(String value) {
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest(value.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}
}
