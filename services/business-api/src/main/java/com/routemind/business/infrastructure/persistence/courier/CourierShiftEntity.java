package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.domain.courier.CourierShift;
import com.routemind.business.domain.courier.CourierShiftStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courier_shifts", schema = "routemind")
class CourierShiftEntity {

	@Id
	@Column(name = "courier_id")
	private UUID courierId;

	@Enumerated(EnumType.STRING)
	@Column(nullable = false, length = 16)
	private CourierShiftStatus status;

	@Version
	@Column(nullable = false)
	private Long version;

	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	protected CourierShiftEntity() {
	}

	static CourierShiftEntity from(CourierShift shift) {
		CourierShiftEntity entity = new CourierShiftEntity();
		entity.apply(shift);
		return entity;
	}

	void apply(CourierShift shift) {
		courierId = shift.courierId();
		status = shift.status();
		updatedAt = shift.updatedAt();
	}

	CourierShift toDomain() {
		return new CourierShift(courierId, status, version == null ? 0 : version, updatedAt);
	}
}
