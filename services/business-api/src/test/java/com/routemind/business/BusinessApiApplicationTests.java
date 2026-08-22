package com.routemind.business;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
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
	void orderCommandsAreIdempotentAndRejectKeyReuse() throws Exception {
		String create = mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", "create-1")
				.header("X-Actor", "customer"))
				.andExpect(status().isCreated())
				.andExpect(jsonPath("$.status").value("CREATED"))
				.andExpect(jsonPath("$.replayed").value(false))
				.andReturn().getResponse().getContentAsString();
		String orderId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
				.readTree(create).get("orderId").asText();

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "transition-1")
					.header("X-Actor", "customer")
					.contentType("application/json")
					.content("{\"target\":\"CONFIRMED\",\"expectedVersion\":0}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("CONFIRMED"))
				.andExpect(jsonPath("$.replayed").value(false));

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "transition-1")
					.header("X-Actor", "customer")
					.contentType("application/json")
					.content("{\"target\":\"CONFIRMED\",\"expectedVersion\":0}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.replayed").value(true));

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "transition-1")
					.header("X-Actor", "customer")
					.contentType("application/json")
					.content("{\"target\":\"CANCELLED\",\"expectedVersion\":1}"))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("idempotency_key_reused"));

		mockMvc.perform(post("/api/v1/orders")
					.header("Idempotency-Key", "create-1")
					.header("X-Actor", "customer"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.replayed").value(true));
	}

	@Test
	void commandWithoutIdempotencyKeyIsRejected() throws Exception {
		mockMvc.perform(post("/api/v1/orders").header("X-Actor", "customer"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("idempotency_key_required"));
	}

	@Test
	void eventStreamRejectsNonCanonicalCursor() throws Exception {
		mockMvc.perform(get("/api/v1/events/stream").param("after", "004"))
				.andExpect(status().isBadRequest());
	}

	@Test
	void orderCommandsRejectUnauthorizedActorAndStaleVersion() throws Exception {
		mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", "unauthorized-create")
				.header("X-Actor", "dispatch"))
				.andExpect(status().isForbidden())
				.andExpect(jsonPath("$.code").value("actor_not_authorized"));

		String create = mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", "stale-create")
				.header("X-Actor", "customer"))
				.andExpect(status().isCreated())
				.andReturn().getResponse().getContentAsString();
		String orderId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
				.readTree(create).get("orderId").asText();

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "stale-transition")
					.header("X-Actor", "customer")
					.contentType("application/json")
					.content("{\"target\":\"CONFIRMED\",\"expectedVersion\":99}"))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("stale_version"));
	}

	@Test
	void flywayOwnsTheApplicationSchema() {
		Integer migrationCount = jdbcTemplate.queryForObject(
				"select count(*) from routemind.flyway_schema_history where version in ('1', '2', '3', '4', '5', '6', '7') and success = true",
				Integer.class);

		assertThat(migrationCount).isEqualTo(7);
	}
}
