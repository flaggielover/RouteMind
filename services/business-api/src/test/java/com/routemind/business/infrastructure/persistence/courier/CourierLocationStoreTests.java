package com.routemind.business.infrastructure.persistence.courier;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.GeoPoint;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class CourierLocationStoreTests {
	@Autowired private CourierLocationStore store;
	@Autowired private JdbcTemplate jdbc;

	@BeforeEach void clear() {
		jdbc.update("delete from routemind.courier_location_history");
		jdbc.update("delete from routemind.courier_locations");
	}

	@Test
	void persistsLocationForProjectionRebuild() {
		CourierLocation location = new CourierLocation(UUID.randomUUID(), new GeoPoint(31.2, 121.5), Instant.parse("2026-01-01T00:00:00Z"));
		store.save(location);
		assertThat(store.findAll()).containsExactly(location);
	}

	@Test
	void keepsOnlyNewerSequenceAndWritesBoundedHistory() {
		UUID courierId = UUID.randomUUID();
		Instant observed = Instant.parse("2026-01-01T00:00:00Z");
		CourierLocation first = new CourierLocation(courierId, new GeoPoint(31.2, 121.5), 1, observed,
				observed.plusSeconds(1), true);
		CourierLocation stale = new CourierLocation(courierId, new GeoPoint(31.3, 121.6), 1, observed.plusSeconds(2),
				observed.plusSeconds(3), true);
		CourierLocation second = new CourierLocation(courierId, new GeoPoint(31.4, 121.7), 2, observed.plusSeconds(4),
				observed.plusSeconds(5), false);

		store.save(first);
		assertThat(store.save(stale)).isEqualTo(first);
		store.save(second);

		assertThat(store.findById(courierId)).isEqualTo(second);
		assertThat(jdbc.queryForObject("select count(*) from routemind.courier_location_history where courier_id = ?",
				Integer.class, courierId)).isEqualTo(2);
		assertThat(jdbc.queryForObject("select online from routemind.courier_locations where courier_id = ?",
				Boolean.class, courierId)).isFalse();
	}
}
