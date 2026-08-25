package com.routemind.business.infrastructure.config;

import com.routemind.business.application.outbox.EventPublisher;
import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.application.outbox.OutboxRelay;
import com.routemind.business.application.security.TenantContext;
import java.time.Clock;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

@Configuration(proxyBeanMethods = false)
@EnableScheduling
public class OutboxModuleConfiguration {

	@Bean
	@ConditionalOnProperty(name = "routemind.rabbit.publisher.enabled", havingValue = "true")
	OutboxRelay outboxRelay(OutboxRepository repository, EventPublisher publisher, Clock clock,
			TenantContext tenants) {
		return new OutboxRelay(repository, publisher, clock, tenants);
	}

	@Bean
	@ConditionalOnBean(OutboxRelay.class)
	OutboxRelayScheduler outboxRelayScheduler(OutboxRelay relay) {
		return new OutboxRelayScheduler(relay);
	}

	static final class OutboxRelayScheduler {
		private final OutboxRelay relay;

		OutboxRelayScheduler(OutboxRelay relay) {
			this.relay = relay;
		}

		@Scheduled(fixedDelayString = "${routemind.rabbit.publisher.relay-delay-ms:1000}")
		void publishDue() {
			relay.publishDue(50);
		}
	}
}
