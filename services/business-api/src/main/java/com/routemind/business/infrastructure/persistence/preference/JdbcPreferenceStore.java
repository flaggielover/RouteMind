package com.routemind.business.infrastructure.persistence.preference;

import com.routemind.business.application.preference.PreferenceAccessDeniedException;
import com.routemind.business.application.preference.PreferenceConflictException;
import com.routemind.business.application.preference.PreferenceDocument;
import com.routemind.business.application.preference.PreferenceIdentity;
import com.routemind.business.application.preference.PreferenceNamespace;
import com.routemind.business.application.preference.PreferenceStore;
import com.routemind.business.application.security.TenantContext;
import java.nio.charset.StandardCharsets;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JdbcPreferenceStore implements PreferenceStore {

	private final JdbcTemplate jdbc;
	private final TenantContext tenants;

	public JdbcPreferenceStore(JdbcTemplate jdbc, TenantContext tenants) {
		this.jdbc = jdbc;
		this.tenants = tenants;
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<PreferenceDocument> find(PreferenceIdentity identity, PreferenceNamespace namespace) {
		List<PreferenceRow> rows = jdbc.query("""
				select owner_role, value_json, version, created_at, updated_at
				from routemind.user_preferences
				where tenant_id = ? and principal_id = ? and namespace = ?
				""", (result, row) -> preference(result), tenants.current().value(), identity.principalId(),
				namespace.id());
		if (rows.isEmpty()) return Optional.empty();
		PreferenceRow row = rows.get(0);
		verifyRole(identity, row.ownerRole());
		return Optional.of(document(namespace, row, false));
	}

	@Override
	@Transactional
	public PreferenceDocument write(PreferenceIdentity identity, PreferenceNamespace namespace, String canonicalValue,
			long expectedVersion, String idempotencyKey, String requestDigest, String valueDigest, Instant changedAt) {
		UUID tenantId = tenants.current().value();
		String operation = "put:" + namespace.id();
		List<CommandRow> commands = jdbc.query("""
				select request_digest, owner_role, response_value_json, response_version,
				       response_created_at, response_updated_at
				from routemind.user_preference_commands
				where tenant_id = ? and principal_id = ? and operation = ? and idempotency_key = ?
				""", (result, row) -> command(result), tenantId, identity.principalId(), operation, idempotencyKey);
		if (!commands.isEmpty()) {
			CommandRow command = commands.get(0);
			verifyRole(identity, command.ownerRole());
			if (!command.requestDigest().equals(requestDigest)) {
				throw new PreferenceConflictException("preference_idempotency_key_reused");
			}
			return new PreferenceDocument(namespace, command.ownerRole(), command.valueJson(), command.version(), true,
					true, command.createdAt(), command.updatedAt());
		}

		List<PreferenceRow> rows = jdbc.query("""
				select owner_role, value_json, version, created_at, updated_at
				from routemind.user_preferences
				where tenant_id = ? and principal_id = ? and namespace = ?
				for update
				""", (result, row) -> preference(result), tenantId, identity.principalId(), namespace.id());
		PreferenceRow existing = rows.isEmpty() ? null : rows.get(0);
		if (existing != null) verifyRole(identity, existing.ownerRole());
		long currentVersion = existing == null ? 0 : existing.version();
		if (currentVersion != expectedVersion) {
			throw new PreferenceConflictException("preference_version_conflict");
		}

		long resultingVersion = currentVersion + 1;
		Instant createdAt = existing == null ? changedAt : existing.createdAt();
		UUID preferenceId = stableId("preference", tenantId, identity.principalId(), namespace.id());
		if (existing == null) {
			jdbc.update("""
					insert into routemind.user_preferences
					(id, tenant_id, principal_id, namespace, owner_role, value_json, version, created_at, updated_at)
					values (?, ?, ?, ?, ?, ?, ?, ?, ?)
					""", preferenceId, tenantId, identity.principalId(), namespace.id(), identity.role(), canonicalValue,
					resultingVersion, createdAt, changedAt);
		}
		else {
			int changed = jdbc.update("""
					update routemind.user_preferences
					set value_json = ?, version = ?, updated_at = ?
					where id = ? and tenant_id = ? and version = ?
					""", canonicalValue, resultingVersion, changedAt, preferenceId, tenantId, currentVersion);
			if (changed != 1) throw new PreferenceConflictException("preference_concurrent_write");
		}

		jdbc.update("""
				insert into routemind.user_preference_audits
				(id, tenant_id, principal_id, namespace, owner_role, operation, idempotency_key,
				 previous_version, resulting_version, value_digest, changed_at)
				values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				""", UUID.randomUUID(), tenantId, identity.principalId(), namespace.id(), identity.role(), operation,
				idempotencyKey, currentVersion, resultingVersion, valueDigest, changedAt);
		jdbc.update("""
				insert into routemind.user_preference_commands
				(id, tenant_id, principal_id, operation, idempotency_key, request_digest, namespace, owner_role,
				 response_value_json, response_version, response_created_at, response_updated_at, created_at)
				values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
				""", stableId("command", tenantId, identity.principalId(), operation, idempotencyKey), tenantId,
				identity.principalId(), operation, idempotencyKey, requestDigest, namespace.id(), identity.role(),
				canonicalValue, resultingVersion, createdAt, changedAt, changedAt);
		return new PreferenceDocument(namespace, identity.role(), canonicalValue, resultingVersion, true, false,
				createdAt, changedAt);
	}

	private static PreferenceRow preference(ResultSet result) throws SQLException {
		return new PreferenceRow(result.getString("owner_role"), result.getString("value_json"),
				result.getLong("version"), result.getTimestamp("created_at").toInstant(),
				result.getTimestamp("updated_at").toInstant());
	}

	private static CommandRow command(ResultSet result) throws SQLException {
		return new CommandRow(result.getString("request_digest"), result.getString("owner_role"),
				result.getString("response_value_json"), result.getLong("response_version"),
				result.getTimestamp("response_created_at").toInstant(),
				result.getTimestamp("response_updated_at").toInstant());
	}

	private static PreferenceDocument document(PreferenceNamespace namespace, PreferenceRow row, boolean replayed) {
		return new PreferenceDocument(namespace, row.ownerRole(), row.valueJson(), row.version(), true, replayed,
				row.createdAt(), row.updatedAt());
	}

	private static void verifyRole(PreferenceIdentity identity, String ownerRole) {
		if (!identity.role().equals(ownerRole)) throw new PreferenceAccessDeniedException();
	}

	private static UUID stableId(String kind, UUID tenantId, String... scope) {
		String joined = kind + "|" + tenantId + "|" + String.join("|", scope);
		return UUID.nameUUIDFromBytes(joined.getBytes(StandardCharsets.UTF_8));
	}

	private record PreferenceRow(String ownerRole, String valueJson, long version, Instant createdAt,
			Instant updatedAt) {
	}

	private record CommandRow(String requestDigest, String ownerRole, String valueJson, long version,
			Instant createdAt, Instant updatedAt) {
	}
}
