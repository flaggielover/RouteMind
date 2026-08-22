package com.routemind.business;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class BusinessApiApplicationTests {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	void actuatorHealthIsAvailable() throws Exception {
		mockMvc.perform(get("/actuator/health"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("UP"));
	}

	@Test
	void systemInfoExposesRuntimeBoundary() throws Exception {
		mockMvc.perform(get("/api/v1/system"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.service").value("business-api"))
				.andExpect(jsonPath("$.runtime").value("java"))
				.andExpect(jsonPath("$.architectureVersion").value("v1"));
	}

	@Test
	void operationsSnapshotIsLiveAndEmptyWhenDurableStateIsEmpty() throws Exception {
		mockMvc.perform(get("/api/v1/operations/snapshot"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.schemaVersion").value("v1"))
				.andExpect(jsonPath("$.source").value("live"))
				.andExpect(jsonPath("$.orders").isArray())
				.andExpect(jsonPath("$.orders").isEmpty())
				.andExpect(jsonPath("$.parties").isArray())
				.andExpect(jsonPath("$.merchants").isArray())
				.andExpect(jsonPath("$.merchants").isEmpty())
				.andExpect(jsonPath("$.courierLocations").isArray())
				.andExpect(jsonPath("$.couriers").isArray())
				.andExpect(jsonPath("$.couriers").isEmpty())
				.andExpect(jsonPath("$.health.status").value("UP"))
				.andExpect(jsonPath("$.health.durableState").value("available"))
				.andExpect(jsonPath("$.health.courierProjection").value("available"));
	}

	@Test
	void requestContextIsReturnedAndPrometheusIsExposed() throws Exception {
		mockMvc.perform(get("/api/v1/system")
				.header("X-Request-Id", "ops-42")
				.header("X-Trace-Id", "0123456789abcdef0123456789abcdef"))
				.andExpect(status().isOk())
				.andExpect(header().string("X-Request-Id", "ops-42"))
				.andExpect(header().string("X-Trace-Id", "0123456789abcdef0123456789abcdef"));

		mockMvc.perform(get("/metrics"))
				.andExpect(status().isOk())
				.andExpect(result -> assertThat(result.getResponse().getContentAsString())
						.contains("routemind_http_requests_total"));
	}

	@Test
	void flywayOwnsTheApplicationSchema() {
		Integer migrationCount = jdbcTemplate.queryForObject(
				"select count(*) from routemind.flyway_schema_history where version in ('1', '2', '3', '4', '5', '6') and success = true",
				Integer.class);

		assertThat(migrationCount).isEqualTo(6);
	}
}
