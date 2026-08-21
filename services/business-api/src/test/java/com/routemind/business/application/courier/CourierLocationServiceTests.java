package com.routemind.business.application.courier;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.GeoPoint;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CourierLocationServiceTests {

	@Test
	void durableWriteSurvivesProjectionOutage() {
		var store = new FakeStore();
		CourierGeoProjection unavailable = new CourierGeoProjection() {
			@Override public void upsert(CourierLocation location) { throw new IllegalStateException("redis down"); }
			@Override public List<com.routemind.business.domain.courier.NearbyCourier> nearby(double lat, double lon, double radius) { return List.of(); }
			@Override public void rebuild(List<CourierLocation> locations) { }
		};
		var service = new CourierLocationService(store, unavailable);
		CourierLocation location = new CourierLocation(UUID.randomUUID(), new GeoPoint(31.2, 121.5), Instant.now());

		assertThat(service.record(location)).isEqualTo(ProjectionWriteStatus.DEGRADED);
		assertThat(store.locations).containsExactly(location);
	}

	private static final class FakeStore implements CourierLocationStore {
		private final List<CourierLocation> locations = new ArrayList<>();
		@Override public CourierLocation save(CourierLocation location) { locations.add(location); return location; }
		@Override public List<CourierLocation> findAll() { return List.copyOf(locations); }
		@Override public CourierLocation findById(UUID courierId) { return locations.stream().filter(l -> l.courierId().equals(courierId)).findFirst().orElseThrow(); }
	}
}
