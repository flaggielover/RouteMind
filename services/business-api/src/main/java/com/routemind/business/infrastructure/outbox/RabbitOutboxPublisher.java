package com.routemind.business.infrastructure.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.outbox.EventPublisher;
import com.routemind.business.domain.event.EventEnvelope;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

@Component
public class RabbitOutboxPublisher implements EventPublisher {

	private final RabbitTemplate rabbitTemplate;
	private final ObjectMapper mapper;

	public RabbitOutboxPublisher(RabbitTemplate rabbitTemplate, ObjectMapper mapper) {
		this.rabbitTemplate = rabbitTemplate;
		this.mapper = mapper;
	}

	@Override
	public void publish(EventEnvelope event) {
		final String payload;
		try {
			Map<String, Object> message = new LinkedHashMap<>();
			message.put("specVersion", event.specVersion());
			message.put("eventId", event.eventId().toString());
			message.put("eventType", event.eventType());
			message.put("occurredAt", event.occurredAt().toString());
			message.put("producer", event.producer());
			message.put("aggregateId", event.aggregateId().toString());
			message.put("aggregateVersion", event.aggregateVersion());
			message.put("correlationId", event.correlationId().toString());
			message.put("causationId", event.causationId() == null ? null : event.causationId().toString());
			message.put("traceId", event.traceId());
			message.put("payload", event.payload());
			payload = mapper.writeValueAsString(message);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalArgumentException("event payload cannot be serialized", exception);
		}
		rabbitTemplate.invoke(operations -> {
			operations.convertAndSend("", "routemind.events." + event.eventType(), payload);
			operations.waitForConfirmsOrDie(5_000);
			return null;
		});
	}
}
