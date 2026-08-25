package com.routemind.business.api.observability;

import java.util.UUID;
import java.util.regex.Pattern;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.tracing.Span;
import io.micrometer.tracing.Tracer;
import com.routemind.business.application.observability.TelemetryAttribution;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public final class RequestObservabilityFilter extends OncePerRequestFilter {

	private static final Logger LOGGER = LoggerFactory.getLogger(RequestObservabilityFilter.class);
	private static final Pattern SAFE_IDENTIFIER = Pattern.compile("[A-Za-z0-9._:-]{1,128}");
	private final MeterRegistry meterRegistry;
	private final Tracer tracer;
	private final TelemetryAttribution telemetry;

	public RequestObservabilityFilter(MeterRegistry meterRegistry, Tracer tracer,
			TelemetryAttribution telemetry) {
		this.meterRegistry = meterRegistry;
		this.tracer = tracer;
		this.telemetry = telemetry;
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
			FilterChain filterChain) throws ServletException, java.io.IOException {
		String requestId = normalize(request.getHeader("X-Request-Id"), UUID.randomUUID().toString());
		Span currentSpan = tracer.currentSpan();
		String otelTraceId = currentSpan == null ? UUID.randomUUID().toString().replace("-", "")
				: currentSpan.context().traceId();
		String traceId = normalize(request.getHeader("X-Trace-Id"), otelTraceId);
		String correlationId = normalize(request.getHeader("X-Correlation-Id"), "");
		long started = System.nanoTime();
		MDC.put("request_id", requestId);
		MDC.put("trace_id", traceId);
		if (currentSpan != null) {
			currentSpan.tag("routemind.request_id", requestId);
			if (!correlationId.isEmpty()) currentSpan.tag("routemind.correlation_id", correlationId);
		}
		response.setHeader("X-Request-Id", requestId);
		response.setHeader("X-Trace-Id", traceId);
		if (currentSpan != null) {
			String traceFlags = Boolean.TRUE.equals(currentSpan.context().sampled()) ? "01" : "00";
			response.setHeader("traceparent", "00-" + currentSpan.context().traceId() + "-"
					+ currentSpan.context().spanId() + "-" + traceFlags);
		}
		try {
			filterChain.doFilter(request, response);
		} finally {
			long durationMicros = (System.nanoTime() - started) / 1_000;
			Object attributed = request.getAttribute(TelemetryAttribution.REQUEST_ATTRIBUTE);
			String tenantKey = attributed instanceof String value ? value
					: TelemetryAttribution.UNATTRIBUTED_KEY;
			if (currentSpan != null) currentSpan.tag("routemind.tenant_key", tenantKey);
			LOGGER.atInfo()
					.addKeyValue("event", "http_request_completed")
					.addKeyValue("method", request.getMethod())
					.addKeyValue("path", request.getRequestURI())
					.addKeyValue("status", response.getStatus())
					.addKeyValue("duration_us", durationMicros)
					.log("HTTP request completed");
			meterRegistry.counter("routemind.http.requests", "method", request.getMethod(),
					"status", Integer.toString(response.getStatus())).increment();
			Timer.builder("routemind.http.request.duration")
					.description("Completed HTTP request duration")
					.tags("method", request.getMethod(), "status", Integer.toString(response.getStatus()))
					.register(meterRegistry).record(durationMicros, java.util.concurrent.TimeUnit.MICROSECONDS);
			telemetry.record("trace", "http", tenantKey);
			telemetry.record("metric", "http", tenantKey);
			MDC.remove("request_id");
			MDC.remove("trace_id");
		}
	}

	private static String normalize(String candidate, String fallback) {
		return candidate != null && SAFE_IDENTIFIER.matcher(candidate).matches() ? candidate : fallback;
	}
}
