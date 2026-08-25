package com.routemind.business.infrastructure.outbox;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.outbox.EventPublisher;
import com.routemind.business.domain.event.EventEnvelope;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

@Component
public class RabbitOutboxPublisher implements EventPublisher {

	private final RabbitTemplate rabbitTemplate;
	private final ObjectMapper mapper;

	public RabbitOutboxPublisher(RabbitTemplate rabbitTemplate, ObjectMapper mapper) {
		this.rabbitTemplate = rabbitTemplate;
		this.rabbitTemplate.setObservationEnabled(true);
		this.mapper = mapper;
	}

	@Override
	public void publish(EventEnvelope event) {
		final String payload;
		try {
			payload = mapper.writeValueAsString(event);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalArgumentException("event payload cannot be serialized", exception);
		}
		rabbitTemplate.invoke(operations -> {
			operations.convertAndSend("", "routemind.events." + event.eventType(), payload,
					message -> addEnvelopeHeaders(message, event));
			operations.waitForConfirmsOrDie(5_000);
			return null;
		});
	}

	static org.springframework.amqp.core.Message addEnvelopeHeaders(
			org.springframework.amqp.core.Message message, EventEnvelope event) {
		message.getMessageProperties().setHeader("X-Trace-Id", event.traceId());
		message.getMessageProperties().setHeader("X-Correlation-Id", event.correlationId().toString());
		message.getMessageProperties().setHeader("X-Event-Id", event.eventId().toString());
		message.getMessageProperties().setHeader("X-Aggregate-Id", event.aggregateId().toString());
		message.getMessageProperties().setHeader("X-Tenant-Id", event.tenantId().toString());
		return message;
	}
}
