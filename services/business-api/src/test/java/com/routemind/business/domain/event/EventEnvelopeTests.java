package com.routemind.business.domain.event;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.routemind.business.domain.security.TenantId;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class EventEnvelopeTests {

	private final ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();

	@Test
	void roundTripsTenantAndDefaultsLegacyForV1PayloadWithoutTenant() throws Exception {
		UUID tenantId = UUID.randomUUID();
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed",
				Instant.parse("2026-01-01T00:00:00Z"), "business-api", tenantId, UUID.randomUUID(), 1,
				UUID.randomUUID(), null, "0123456789abcdef0123456789abcdef", Map.of("status", "ASSIGNED"));

		String json = mapper.writeValueAsString(event);
		assertThat(mapper.readValue(json, EventEnvelope.class)).isEqualTo(event);

		ObjectNode legacyJson = (ObjectNode) mapper.readTree(json);
		legacyJson.remove("tenantId");
		EventEnvelope legacy = mapper.treeToValue(legacyJson, EventEnvelope.class);
		assertThat(legacy.tenantId()).isEqualTo(TenantId.LEGACY.value());
	}

	@Test
	void rejectsNilTenant() {
		assertThatThrownBy(() -> new EventEnvelope("1.0", UUID.randomUUID(), "order.status.changed",
				Instant.EPOCH, "business-api", new UUID(0, 0), UUID.randomUUID(), 1, UUID.randomUUID(),
				null, "0123456789abcdef0123456789abcdef", Map.of()))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessage("tenantId must not be the nil UUID");
	}
}
