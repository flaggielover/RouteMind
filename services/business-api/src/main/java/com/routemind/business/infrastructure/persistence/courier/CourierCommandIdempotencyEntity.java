package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierCommandIdempotency;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courier_command_idempotency", schema = "routemind")
class CourierCommandIdempotencyEntity {

	@Id
	@Column(name = "idempotency_key", length = 128)
	private String key;
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

	static CourierCommandIdempotencyEntity from(CourierCommandIdempotency record) {
		CourierCommandIdempotencyEntity entity = new CourierCommandIdempotencyEntity();
		entity.apply(record);
		return entity;
	}

	void apply(CourierCommandIdempotency record) {
		key = record.key();
		requestHash = record.requestHash();
		operation = record.operation();
		courierId = record.courierId();
		responseStatus = record.status();
		responseVersion = record.version();
		createdAt = record.createdAt();
	}

	CourierCommandIdempotency toDomain() {
		return new CourierCommandIdempotency(key, requestHash, operation, courierId, responseStatus, responseVersion,
				createdAt);
	}
}
