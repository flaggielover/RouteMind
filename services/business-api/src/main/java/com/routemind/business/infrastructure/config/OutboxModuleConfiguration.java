package com.routemind.business.infrastructure.config;

import com.routemind.business.application.outbox.EventPublisher;
import com.routemind.business.application.outbox.OutboxRelay;
import java.time.Clock;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import com.routemind.business.application.outbox.OutboxRepository;

@Configuration(proxyBeanMethods = false)
public class OutboxModuleConfiguration {

	@Bean
	@ConditionalOnProperty(name = "routemind.rabbit.publisher.enabled", havingValue = "true")
	OutboxRelay outboxRelay(OutboxRepository repository, EventPublisher publisher, Clock clock) {
		return new OutboxRelay(repository, publisher, clock);
	}
}
