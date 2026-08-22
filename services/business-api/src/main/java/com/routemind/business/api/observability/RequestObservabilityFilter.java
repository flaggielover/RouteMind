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
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public final class RequestObservabilityFilter extends OncePerRequestFilter {

	private static final Logger LOGGER = LoggerFactory.getLogger(RequestObservabilityFilter.class);
	private static final Pattern SAFE_IDENTIFIER = Pattern.compile("[A-Za-z0-9._:-]{1,128}");
	private final MeterRegistry meterRegistry;

	public RequestObservabilityFilter(MeterRegistry meterRegistry) {
		this.meterRegistry = meterRegistry;
	}

	@Override
	protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
			FilterChain filterChain) throws ServletException, java.io.IOException {
		String requestId = normalize(request.getHeader("X-Request-Id"), UUID.randomUUID().toString());
		String traceId = normalize(request.getHeader("X-Trace-Id"), UUID.randomUUID().toString().replace("-", ""));
		long started = System.nanoTime();
		MDC.put("request_id", requestId);
		MDC.put("trace_id", traceId);
		response.setHeader("X-Request-Id", requestId);
		response.setHeader("X-Trace-Id", traceId);
		try {
			filterChain.doFilter(request, response);
		} finally {
			long durationMicros = (System.nanoTime() - started) / 1_000;
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
			MDC.remove("request_id");
			MDC.remove("trace_id");
		}
	}

	private static String normalize(String candidate, String fallback) {
		return candidate != null && SAFE_IDENTIFIER.matcher(candidate).matches() ? candidate : fallback;
	}
}
