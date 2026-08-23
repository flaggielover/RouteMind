package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.GeoPoint;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courier_location_history", schema = "routemind")
class CourierLocationHistoryEntity {
	@Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
	@Column(name = "courier_id", nullable = false) private UUID courierId;
	@Column(name = "location_sequence", nullable = false) private long sequence;
	@Column(nullable = false) private double latitude;
	@Column(nullable = false) private double longitude;
	@Column(name = "observed_at", nullable = false) private Instant observedAt;
	@Column(name = "ingested_at", nullable = false) private Instant ingestedAt;
	@Column(nullable = false) private boolean online;

	protected CourierLocationHistoryEntity() { }

	static CourierLocationHistoryEntity from(CourierLocation location) {
		CourierLocationHistoryEntity entity = new CourierLocationHistoryEntity();
		entity.courierId = location.courierId();
		entity.sequence = location.sequence();
		entity.latitude = location.point().latitude();
		entity.longitude = location.point().longitude();
		entity.observedAt = location.observedAt();
		entity.ingestedAt = location.ingestedAt();
		entity.online = location.online();
		return entity;
	}

	CourierLocation toDomain() {
		return new CourierLocation(courierId, new GeoPoint(latitude, longitude), sequence, observedAt,
				ingestedAt, online);
	}
}
