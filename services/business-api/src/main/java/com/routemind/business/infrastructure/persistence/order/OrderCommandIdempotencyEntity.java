package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.application.order.OrderCommandIdempotency;
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
@Table(name = "order_command_idempotency", schema = "routemind")
class OrderCommandIdempotencyEntity extends TenantScopedEntity {

	@Id
	@Column(name = "idempotency_key", length = 128)
	private String key;

	@Column(name = "logical_key", nullable = false, length = 128)
	private String logicalKey;

	@Column(name = "request_hash", nullable = false, length = 64)
	private String requestHash;

	@Column(nullable = false, length = 32)
	private String operation;

	@Column(name = "order_id", nullable = false)
	private UUID orderId;

	@Column(name = "response_status", nullable = false, length = 32)
	private String responseStatus;

	@Column(name = "response_version", nullable = false)
	private long responseVersion;

	@Column(name = "created_at", nullable = false)
	private Instant createdAt;

	protected OrderCommandIdempotencyEntity() {
	}

	private OrderCommandIdempotencyEntity(OrderCommandIdempotency record, UUID tenantId) {
		assignTenant(tenantId);
		key = TenantKey.encode(tenantId, record.key());
		logicalKey = record.key();
		apply(record);
	}

	static OrderCommandIdempotencyEntity from(OrderCommandIdempotency record, UUID tenantId) {
		return new OrderCommandIdempotencyEntity(record, tenantId);
	}

	void apply(OrderCommandIdempotency record) {
		if (logicalKey != null && !logicalKey.equals(record.key())) throw new TenantIsolationException();
		logicalKey = record.key();
		requestHash = record.requestHash();
		operation = record.operation();
		orderId = record.orderId();
		responseStatus = record.status();
		responseVersion = record.version();
		createdAt = record.createdAt();
	}

	OrderCommandIdempotency toDomain() {
		return new OrderCommandIdempotency(logicalKey, requestHash, operation, orderId, responseStatus, responseVersion,
				createdAt);
	}
}
