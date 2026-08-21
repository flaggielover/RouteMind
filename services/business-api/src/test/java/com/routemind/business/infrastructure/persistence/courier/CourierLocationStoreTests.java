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

	@BeforeEach void clear() { jdbc.update("delete from routemind.courier_locations"); }

	@Test
	void persistsLocationForProjectionRebuild() {
		CourierLocation location = new CourierLocation(UUID.randomUUID(), new GeoPoint(31.2, 121.5), Instant.parse("2026-01-01T00:00:00Z"));
		store.save(location);
		assertThat(store.findAll()).containsExactly(location);
	}
}
