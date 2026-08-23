package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.GeoPoint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courier_locations", schema = "routemind")
class CourierLocationEntity {
	@Id private UUID courierId;
	@Column(nullable = false) private double latitude;
	@Column(nullable = false) private double longitude;
	@Column(name = "location_sequence", nullable = false) private long sequence;
	@Column(name = "observed_at", nullable = false) private Instant observedAt;
	@Column(name = "ingested_at", nullable = false) private Instant ingestedAt;
	@Column(nullable = false) private boolean online;

	protected CourierLocationEntity() {
	}

	static CourierLocationEntity from(CourierLocation location) {
		CourierLocationEntity entity = new CourierLocationEntity();
		entity.apply(location);
		return entity;
	}

	void apply(CourierLocation location) {
		courierId = location.courierId();
		latitude = location.point().latitude();
		longitude = location.point().longitude();
		sequence = location.sequence();
		observedAt = location.observedAt();
		ingestedAt = location.ingestedAt();
		online = location.online();
	}

	CourierLocation toDomain() {
		return new CourierLocation(courierId, new GeoPoint(latitude, longitude), sequence, observedAt,
				ingestedAt, online);
	}

	long sequence() { return sequence; }
}
