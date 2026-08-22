package com.routemind.business.api.observability;

import io.micrometer.prometheusmetrics.PrometheusConfig;
import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration(proxyBeanMethods = false)
public class MetricsConfiguration {

	@Bean
	@Primary
	public PrometheusMeterRegistry prometheusMeterRegistry() {
		return new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
	}
}
