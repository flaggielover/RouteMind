package com.routemind.business.infrastructure.outbox;

import com.routemind.business.application.outbox.EventPublisher;
import com.routemind.business.domain.event.EventEnvelope;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

@Component
public class RabbitOutboxPublisher implements EventPublisher {

	private final RabbitTemplate rabbitTemplate;

	public RabbitOutboxPublisher(RabbitTemplate rabbitTemplate) {
		this.rabbitTemplate = rabbitTemplate;
	}

	@Override
	public void publish(EventEnvelope event) {
		rabbitTemplate.invoke(operations -> {
			operations.convertAndSend("", "routemind.events." + event.eventType(), event);
			operations.waitForConfirmsOrDie(5_000);
			return null;
		});
	}
}
