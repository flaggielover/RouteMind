package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.application.order.OrderCommandIdempotency;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "order_command_idempotency", schema = "routemind")
class OrderCommandIdempotencyEntity {

	@Id
	@Column(name = "idempotency_key", length = 128)
	private String key;

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

	private OrderCommandIdempotencyEntity(OrderCommandIdempotency record) {
		apply(record);
	}

	static OrderCommandIdempotencyEntity from(OrderCommandIdempotency record) {
		return new OrderCommandIdempotencyEntity(record);
	}

	void apply(OrderCommandIdempotency record) {
		key = record.key();
		requestHash = record.requestHash();
		operation = record.operation();
		orderId = record.orderId();
		responseStatus = record.status();
		responseVersion = record.version();
		createdAt = record.createdAt();
	}

	OrderCommandIdempotency toDomain() {
		return new OrderCommandIdempotency(key, requestHash, operation, orderId, responseStatus, responseVersion,
				createdAt);
	}
}
