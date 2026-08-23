package com.routemind.business.infrastructure.outbox;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.domain.event.EventEnvelope;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;

class RabbitOutboxPublisherTests {

	@Test
	void preservesTraceAndBusinessIdentityInMessageHeaders() {
		UUID eventId = UUID.randomUUID();
		UUID orderId = UUID.randomUUID();
		UUID correlationId = UUID.randomUUID();
		String traceId = "0123456789abcdef0123456789abcdef";
		EventEnvelope event = new EventEnvelope("1.0", eventId, "order.assigned", Instant.EPOCH,
				"business-api", orderId, 2, correlationId, null, traceId, Map.of());

		Message message = RabbitOutboxPublisher.addEnvelopeHeaders(MessageBuilder.withBody(new byte[0]).build(), event);

		assertThat((Object) message.getMessageProperties().getHeader("X-Trace-Id")).isEqualTo(traceId);
		assertThat((Object) message.getMessageProperties().getHeader("X-Correlation-Id"))
				.isEqualTo(correlationId.toString());
		assertThat((Object) message.getMessageProperties().getHeader("X-Event-Id")).isEqualTo(eventId.toString());
		assertThat((Object) message.getMessageProperties().getHeader("X-Aggregate-Id"))
				.isEqualTo(orderId.toString());
	}
}
