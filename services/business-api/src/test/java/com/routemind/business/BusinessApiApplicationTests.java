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
		jdbcTemplate.update("delete from routemind.courier_command_idempotency");
		jdbcTemplate.update("delete from routemind.courier_shifts");
		jdbcTemplate.update("delete from routemind.order_command_idempotency");
		jdbcTemplate.update("delete from routemind.order_transitions");
		jdbcTemplate.update("delete from routemind.orders");
		jdbcTemplate.update("delete from routemind.outbox_messages");
		jdbcTemplate.update("delete from routemind.inbox_messages");
		jdbcTemplate.update("delete from routemind.courier_locations");
		jdbcTemplate.update("delete from routemind.parties");
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
				.andExpect(header().exists("X-Trace-Id"))
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
	void merchantPreparationCommandsAreValidatedAndAudited() throws Exception {
		String create = mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", "merchant-flow-create")
				.header("X-Actor", "customer"))
				.andExpect(status().isCreated())
				.andReturn().getResponse().getContentAsString();
		String orderId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
				.readTree(create).get("orderId").asText();

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "merchant-confirm")
					.header("X-Actor", "merchant")
					.contentType("application/json")
					.content("{\"target\":\"CONFIRMED\",\"expectedVersion\":0}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("CONFIRMED"));

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "merchant-preparing")
					.header("X-Actor", "merchant")
					.contentType("application/json")
					.content("{\"target\":\"PREPARING\",\"expectedVersion\":1}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("PREPARING"));

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "merchant-ready")
					.header("X-Actor", "merchant")
					.contentType("application/json")
					.content("{\"target\":\"READY_FOR_PICKUP\",\"expectedVersion\":2}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("READY_FOR_PICKUP"));

		mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
					.header("Idempotency-Key", "merchant-invalid")
					.header("X-Actor", "merchant")
					.contentType("application/json")
					.content("{\"target\":\"ASSIGNED\",\"expectedVersion\":3}"))
				.andExpect(status().isForbidden())
				.andExpect(jsonPath("$.code").value("actor_not_authorized"));
	}

	@Test
	void advancedDispatchAssignmentIsVersionedAuditedAndIdempotent() throws Exception {
		String create = mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", "rm136-create")
				.header("X-Actor", "customer"))
				.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
		String orderId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
				.readTree(create).get("orderId").asText();
		transition(mockMvc, orderId, "rm136-confirm", "customer", "CONFIRMED", 0)
				.andExpect(status().isOk());
		String courierId = java.util.UUID.randomUUID().toString();
		String body = "{\"requestId\":\"compute-request-1\",\"contractVersion\":\"v1\","
				+ "\"courierId\":\"" + courierId + "\",\"strategy\":\"risk-aware\","
				+ "\"strategyVersion\":\"1.0.0\",\"inputDigest\":\""
				+ "0000000000000000000000000000000000000000000000000000000000000000"
				+ "\",\"outputDigest\":\""
				+ "1111111111111111111111111111111111111111111111111111111111111111"
				+ "\",\"fallbackUsed\":true,\"fallbackReason\":\"travel-provider-timeout\","
				+ "\"expectedOrderVersion\":1}";
		mockMvc.perform(post("/api/v1/orders/{orderId}/dispatch-assignment", orderId)
				.header("Idempotency-Key", "rm136-assignment")
				.header("X-Trace-Id", "0123456789abcdef0123456789abcdef")
				.contentType("application/json").content(body))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("ASSIGNED"))
				.andExpect(jsonPath("$.version").value(2))
				.andExpect(jsonPath("$.replayed").value(false))
				.andExpect(jsonPath("$.contractVersion").value("v1"))
				.andExpect(jsonPath("$.fallbackUsed").value(true))
				.andExpect(jsonPath("$.leaseId").isNotEmpty())
				.andExpect(jsonPath("$.leaseGeneration").value(1));

		mockMvc.perform(post("/api/v1/orders/{orderId}/dispatch-assignment", orderId)
				.header("Idempotency-Key", "rm136-assignment")
				.contentType("application/json").content(body))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.replayed").value(true));

		String changed = body.replace("risk-aware", "nearest");
		mockMvc.perform(post("/api/v1/orders/{orderId}/dispatch-assignment", orderId)
				.header("Idempotency-Key", "rm136-assignment")
				.contentType("application/json").content(changed))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("idempotency_key_reused"));

		mockMvc.perform(post("/api/v1/orders/{orderId}/dispatch-assignment", orderId)
				.header("Idempotency-Key", "rm136-stale")
				.contentType("application/json").content(body))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("stale_version"));
		assertThat(jdbcTemplate.queryForObject(
				"select count(*) from routemind.dispatch_assignment_audits", Integer.class)).isOne();
		assertThat(jdbcTemplate.queryForObject(
				"select count(*) from routemind.outbox_messages where event_type = 'dispatch.assignment.applied'",
				Integer.class)).isOne();
		assertThat(jdbcTemplate.queryForObject(
				"select payload_json from routemind.outbox_messages where event_type = 'dispatch.assignment.applied'",
				String.class)).contains("risk-aware", "travel-provider-timeout", "inputDigest");
		assertThat(jdbcTemplate.queryForObject(
				"select lease_generation from routemind.dispatch_assignment_audits where idempotency_key = 'rm136-assignment'",
				Long.class)).isEqualTo(1L);
		assertThat(jdbcTemplate.queryForObject(
				"select count(*) from routemind.dispatch_decision_ledger where decision_id = 'compute-request-1'",
				Integer.class)).isOne();
		assertThat(jdbcTemplate.queryForObject(
				"select clock_domain from routemind.dispatch_decision_ledger where decision_id = 'compute-request-1'",
				String.class)).isEqualTo("WALL");
		assertThat(jdbcTemplate.queryForObject(
				"select input_snapshot_json || output_snapshot_json from routemind.dispatch_decision_ledger where decision_id = 'compute-request-1'",
				String.class)).contains("reference_data_id", "strategy_version", "input_digest", "output_digest");
	}

	@Test
	void assignmentLeasePreventsOneCourierBeingCommittedToTwoOrders() throws Exception {
		String courierId = java.util.UUID.randomUUID().toString();
		String firstOrder = createConfirmedOrder("lease-order-1");
		String secondOrder = createConfirmedOrder("lease-order-2");

		mockMvc.perform(post("/api/v1/orders/{orderId}/dispatch-assignment", firstOrder)
				.header("Idempotency-Key", "lease-assignment-1")
				.contentType("application/json").content(dispatchBody(courierId, "lease-decision-1", 1)))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("ASSIGNED"));

		mockMvc.perform(post("/api/v1/orders/{orderId}/dispatch-assignment", secondOrder)
				.header("Idempotency-Key", "lease-assignment-2")
				.contentType("application/json").content(dispatchBody(courierId, "lease-decision-2", 1)))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("courier_already_assigned"));

		assertThat(jdbcTemplate.queryForObject(
				"select count(*) from routemind.dispatch_assignment_leases where courier_id = ? and state = 'COMMITTED'",
				Integer.class, java.util.UUID.fromString(courierId))).isOne();
		assertThat(jdbcTemplate.queryForObject(
				"select count(*) from routemind.dispatch_assignment_lease_events where courier_id = ?",
				Integer.class, java.util.UUID.fromString(courierId))).isEqualTo(2);
	}

	private String createConfirmedOrder(String key) throws Exception {
		String create = mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", key + "-create")
				.header("X-Actor", "customer"))
				.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
		String orderId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
				.readTree(create).get("orderId").asText();
		transition(mockMvc, orderId, key + "-confirm", "customer", "CONFIRMED", 0)
				.andExpect(status().isOk());
		return orderId;
	}

	private static String dispatchBody(String courierId, String decisionId, long expectedVersion) {
		return "{\"requestId\":\"" + decisionId + "\",\"contractVersion\":\"v1\","
				+ "\"courierId\":\"" + courierId + "\",\"strategy\":\"risk-aware\","
				+ "\"strategyVersion\":\"1.0.0\",\"inputDigest\":\""
				+ "0000000000000000000000000000000000000000000000000000000000000000"
				+ "\",\"outputDigest\":\""
				+ "1111111111111111111111111111111111111111111111111111111111111111"
				+ "\",\"fallbackUsed\":false,\"expectedOrderVersion\":" + expectedVersion + "}";
	}

	@Test
	void courierShiftLocationAndDeliveryCommandsAreDurableAndIdempotent() throws Exception {
		String courierId = java.util.UUID.randomUUID().toString();
		mockMvc.perform(post("/api/v1/couriers/{courierId}/shift", courierId)
				.header("Idempotency-Key", "courier-online")
				.header("X-Actor", "courier")
				.contentType("application/json")
				.content("{\"target\":\"ONLINE\",\"expectedVersion\":0}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("ONLINE"))
				.andExpect(jsonPath("$.version").value(1));

		mockMvc.perform(post("/api/v1/couriers/{courierId}/shift", courierId)
				.header("Idempotency-Key", "courier-online")
				.header("X-Actor", "courier")
				.contentType("application/json")
				.content("{\"target\":\"ONLINE\",\"expectedVersion\":0}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.replayed").value(true));

		mockMvc.perform(post("/api/v1/couriers/{courierId}/location", courierId)
				.header("Idempotency-Key", "courier-location-1")
				.header("X-Actor", "courier")
				.contentType("application/json")
				.content("{\"latitude\":31.2,\"longitude\":121.5,\"observedAt\":\"2026-08-22T12:00:00Z\"}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("DEGRADED"));

		String create = mockMvc.perform(post("/api/v1/orders")
				.header("Idempotency-Key", "courier-flow-create")
				.header("X-Actor", "customer"))
				.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
		String orderId = com.fasterxml.jackson.databind.json.JsonMapper.builder().build()
				.readTree(create).get("orderId").asText();
		transition(mockMvc, orderId, "courier-flow-confirm", "customer", "CONFIRMED", 0)
				.andExpect(status().isOk());
		transition(mockMvc, orderId, "courier-flow-assign", "dispatch", "ASSIGNED", 1)
				.andExpect(status().isOk());
		transition(mockMvc, orderId, "courier-flow-accept", "courier", "ACCEPTED", 2)
				.andExpect(jsonPath("$.status").value("ACCEPTED"));
		transition(mockMvc, orderId, "courier-flow-arrive", "courier", "ARRIVED", 3)
				.andExpect(jsonPath("$.status").value("ARRIVED"));
		transition(mockMvc, orderId, "courier-flow-pickup", "courier", "PICKED_UP", 4)
				.andExpect(jsonPath("$.status").value("PICKED_UP"));
		transition(mockMvc, orderId, "courier-flow-deliver", "courier", "DELIVERED", 5)
				.andExpect(jsonPath("$.status").value("DELIVERED"));
	}

	private static org.springframework.test.web.servlet.ResultActions transition(
			org.springframework.test.web.servlet.MockMvc mockMvc, String orderId, String key, String actor,
			String target, long expectedVersion) throws Exception {
		return mockMvc.perform(post("/api/v1/orders/{orderId}/transitions", orderId)
				.header("Idempotency-Key", key)
				.header("X-Actor", actor)
				.contentType("application/json")
				.content("{\"target\":\"" + target + "\",\"expectedVersion\":" + expectedVersion + "}"));
	}

	@Test
	void flywayOwnsTheApplicationSchema() {
		Integer migrationCount = jdbcTemplate.queryForObject(
				"select count(*) from routemind.flyway_schema_history where version in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12') and success = true",
				Integer.class);

		assertThat(migrationCount).isEqualTo(12);
	}
}
