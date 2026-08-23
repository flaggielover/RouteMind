package com.routemind.business.api.courier;

import com.routemind.business.application.courier.CourierCommandAuthorizationException;
import com.routemind.business.application.courier.CourierCommandConflictException;
import com.routemind.business.application.courier.CourierCommandResult;
import com.routemind.business.application.courier.CourierLocationCommandService;
import com.routemind.business.application.courier.CourierShiftCommandService;
import com.routemind.business.domain.courier.CourierShiftStatus;
import java.time.Clock;
import java.time.Instant;
import java.util.Locale;
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/couriers")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public final class CourierCommandController {

	private static final Pattern TRACE_ID = Pattern.compile("[0-9a-f]{32}");
	private final CourierShiftCommandService shifts;
	private final CourierLocationCommandService locations;
	private final Clock clock;

	public CourierCommandController(CourierShiftCommandService shifts, CourierLocationCommandService locations,
			Clock clock) {
		this.shifts = shifts;
		this.locations = locations;
		this.clock = clock;
	}

	@PostMapping("/{courierId}/shift")
	public CourierCommandResponse shift(@PathVariable UUID courierId,
			@RequestHeader("Idempotency-Key") String idempotencyKey, @RequestHeader("X-Actor") String actor,
			@RequestHeader(value = "X-Correlation-Id", required = false) String correlationId,
			@RequestBody ShiftRequest request) {
		if (request == null) throw new IllegalArgumentException("shift request is required");
		CourierShiftStatus target = parseShiftStatus(request.target());
		CourierCommandResult result = shifts.transition(courierId, target, normalizeActor(actor),
				request.expectedVersion(), correlation(correlationId), traceId(), idempotencyKey);
		return CourierCommandResponse.from(result, traceId());
	}

	@PostMapping("/{courierId}/location")
	public CourierCommandResponse location(@PathVariable UUID courierId,
			@RequestHeader("Idempotency-Key") String idempotencyKey, @RequestHeader("X-Actor") String actor,
			@RequestHeader(value = "X-Correlation-Id", required = false) String correlationId,
			@RequestBody LocationRequest request) {
		if (request == null) throw new IllegalArgumentException("location request is required");
		Instant observedAt = request.observedAt() == null || request.observedAt().isBlank()
				? Instant.now(clock) : Instant.parse(request.observedAt());
		long sequence = request.sequence() == null ? 1 : request.sequence();
		boolean online = request.online() == null || request.online();
		CourierCommandResult result = locations.record(courierId, request.latitude(), request.longitude(), sequence,
				observedAt, online, normalizeActor(actor), correlation(correlationId), traceId(), idempotencyKey);
		return CourierCommandResponse.from(result, traceId());
	}

	@ExceptionHandler(CourierCommandAuthorizationException.class)
	ResponseEntity<ErrorResponse> forbidden(CourierCommandAuthorizationException exception) {
		return error(HttpStatus.FORBIDDEN, exception.getMessage());
	}

	@ExceptionHandler(CourierCommandConflictException.class)
	ResponseEntity<ErrorResponse> conflict(CourierCommandConflictException exception) {
		return error(HttpStatus.CONFLICT, exception.getMessage());
	}

	@ExceptionHandler(IllegalStateException.class)
	ResponseEntity<ErrorResponse> invalidState(IllegalStateException exception) {
		return error(HttpStatus.CONFLICT, exception.getMessage());
	}

	@ExceptionHandler({ IllegalArgumentException.class, MissingRequestHeaderException.class })
	ResponseEntity<ErrorResponse> invalidRequest(Exception exception) {
		String code = exception instanceof MissingRequestHeaderException missing
				&& "Idempotency-Key".equalsIgnoreCase(missing.getHeaderName())
				? "idempotency_key_required" : "invalid_request";
		return error(HttpStatus.BAD_REQUEST, code);
	}

	private ResponseEntity<ErrorResponse> error(HttpStatus status, String code) {
		return ResponseEntity.status(status).body(new ErrorResponse(code, traceId()));
	}

	private static String normalizeActor(String actor) {
		if (actor == null || actor.isBlank()) throw new IllegalArgumentException("actor is required");
		return actor.trim().toLowerCase(Locale.ROOT);
	}

	private static UUID correlation(String value) {
		return value == null || value.isBlank() ? UUID.randomUUID() : UUID.fromString(value);
	}

	private static String traceId() {
		String value = MDC.get("trace_id");
		return value != null && TRACE_ID.matcher(value).matches() ? value : "00000000000000000000000000000000";
	}

	private static CourierShiftStatus parseShiftStatus(String target) {
		if (target == null || target.isBlank()) throw new IllegalArgumentException("target is required");
		return CourierShiftStatus.valueOf(target.trim().toUpperCase(Locale.ROOT));
	}

	public record ShiftRequest(String target, long expectedVersion) { }

	public record LocationRequest(double latitude, double longitude, String observedAt, Long sequence, Boolean online) { }

	public record CourierCommandResponse(UUID courierId, String status, long version, boolean replayed, String traceId) {
		static CourierCommandResponse from(CourierCommandResult result, String traceId) {
			return new CourierCommandResponse(result.courierId(), result.status(), result.version(), result.replayed(), traceId);
		}
	}

	public record ErrorResponse(String code, String traceId) { }
}
