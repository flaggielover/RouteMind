package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierCommandIdempotency;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.infrastructure.persistence.TenantKey;
import com.routemind.business.infrastructure.persistence.TenantScopedEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courier_command_idempotency", schema = "routemind")
class CourierCommandIdempotencyEntity extends TenantScopedEntity {

	@Id
	@Column(name = "idempotency_key", length = 128)
	private String key;
	@Column(name = "logical_key", nullable = false, length = 128)
	private String logicalKey;
	@Column(name = "request_hash", nullable = false, length = 64)
	private String requestHash;
	@Column(nullable = false, length = 32)
	private String operation;
	@Column(name = "courier_id", nullable = false)
	private UUID courierId;
	@Column(name = "response_status", nullable = false, length = 16)
	private String responseStatus;
	@Column(name = "response_version", nullable = false)
	private long responseVersion;
	@Column(name = "created_at", nullable = false)
	private Instant createdAt;

	protected CourierCommandIdempotencyEntity() {
	}

	static CourierCommandIdempotencyEntity from(CourierCommandIdempotency record, UUID tenantId) {
		CourierCommandIdempotencyEntity entity = new CourierCommandIdempotencyEntity();
		entity.assignTenant(tenantId);
		entity.key = TenantKey.encode(tenantId, record.key());
		entity.logicalKey = record.key();
		entity.apply(record);
		return entity;
	}

	void apply(CourierCommandIdempotency record) {
		if (logicalKey != null && !logicalKey.equals(record.key())) throw new TenantIsolationException();
		logicalKey = record.key();
		requestHash = record.requestHash();
		operation = record.operation();
		courierId = record.courierId();
		responseStatus = record.status();
		responseVersion = record.version();
		createdAt = record.createdAt();
	}

	CourierCommandIdempotency toDomain() {
		return new CourierCommandIdempotency(logicalKey, requestHash, operation, courierId, responseStatus, responseVersion,
				createdAt);
	}
}
