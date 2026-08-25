package com.routemind.business.application.preference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class UserPreferenceServiceTests {

	private static final Instant NOW = Instant.parse("2026-08-25T00:00:00Z");
	private PreferenceMemoryStore store;
	private UserPreferenceService service;

	@BeforeEach
	void setUp() {
		store = new PreferenceMemoryStore();
		PreferencePayloadPolicy policy = new PreferencePayloadPolicy(new ObjectMapper());
		service = new UserPreferenceService(store, policy, Clock.fixed(NOW, ZoneOffset.UTC));
	}

	@Test
	void missingPreferenceReturnsExplicitDefaultAtVersionZero() {
		PreferenceDocument document = service.read(new PreferenceIdentity("subject-1", "customer"),
				PreferenceNamespace.LOCALE);
		assertThat(document.persisted()).isFalse();
		assertThat(document.version()).isZero();
		assertThat(document.valueJson()).isEqualTo("{\"locale\":\"en-US\",\"timeZone\":\"UTC\"}");
	}

	@Test
	void writeRequiresVersionAndIdempotencyAndReplaysSameRequest() throws Exception {
		PreferenceIdentity identity = new PreferenceIdentity("subject-1", "customer");
		var value = new ObjectMapper().readTree("{\"locale\":\"zh-CN\",\"timeZone\":\"Asia/Shanghai\"}");
		PreferenceDocument first = service.write(identity, PreferenceNamespace.LOCALE, value, 0, "key-1");
		PreferenceDocument replay = service.write(identity, PreferenceNamespace.LOCALE, value, 0, "key-1");
		assertThat(first.version()).isEqualTo(1);
		assertThat(first.replayed()).isFalse();
		assertThat(replay.replayed()).isTrue();
		assertThat(store.auditCount).isEqualTo(1);
		assertThatThrownBy(() -> service.write(identity, PreferenceNamespace.LOCALE, value, 0, "key-2"))
				.isInstanceOf(PreferenceConflictException.class).hasMessage("preference_version_conflict");
	}

	@Test
	void unsupportedRoleAndNamespaceFailClosed() throws Exception {
		var value = new ObjectMapper().readTree("{\"locale\":\"en-US\",\"timeZone\":\"UTC\"}");
		assertThatThrownBy(() -> service.read(new PreferenceIdentity("subject-1", "unknown"), PreferenceNamespace.LOCALE))
				.isInstanceOf(PreferenceAccessDeniedException.class);
		assertThatThrownBy(() -> service.write(new PreferenceIdentity("subject-1", "customer"),
				PreferenceNamespace.LOCALE, value, 0, "bad key with spaces"))
				.isInstanceOf(IllegalArgumentException.class).hasMessage("idempotency_key_invalid");
	}

	private static final class PreferenceMemoryStore implements PreferenceStore {
		private final Map<String, PreferenceDocument> values = new HashMap<>();
		private final Map<String, String> commands = new HashMap<>();
		private int auditCount;

		@Override
		public Optional<PreferenceDocument> find(PreferenceIdentity identity, PreferenceNamespace namespace) {
			return Optional.ofNullable(values.get(identity.principalId() + "|" + namespace.id()));
		}

		@Override
		public PreferenceDocument write(PreferenceIdentity identity, PreferenceNamespace namespace, String canonicalValue,
				long expectedVersion, String idempotencyKey, String requestDigest, String valueDigest, Instant changedAt) {
			String commandKey = identity.principalId() + "|" + namespace.id() + "|" + idempotencyKey;
			if (commands.containsKey(commandKey)) {
				PreferenceDocument replay = values.get(identity.principalId() + "|" + namespace.id());
				return new PreferenceDocument(replay.namespace(), replay.ownerRole(), replay.valueJson(), replay.version(),
						true, true, replay.createdAt(), replay.updatedAt());
			}
			String key = identity.principalId() + "|" + namespace.id();
			PreferenceDocument existing = values.get(key);
			if (existing != null && existing.version() != expectedVersion) throw new PreferenceConflictException("preference_version_conflict");
			long version = expectedVersion + 1;
			PreferenceDocument result = new PreferenceDocument(namespace, identity.role(), canonicalValue, version, true,
					false, changedAt, changedAt);
			values.put(key, result);
			commands.put(commandKey, requestDigest);
			auditCount++;
			return result;
		}
	}
}
