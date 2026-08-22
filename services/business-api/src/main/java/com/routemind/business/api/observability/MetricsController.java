package com.routemind.business.api.observability;

import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/metrics")
public final class MetricsController {

	private final PrometheusMeterRegistry registry;

	public MetricsController(PrometheusMeterRegistry registry) {
		this.registry = registry;
	}

	@GetMapping(produces = MediaType.TEXT_PLAIN_VALUE)
	public String scrape() {
		return registry.scrape();
	}
}
