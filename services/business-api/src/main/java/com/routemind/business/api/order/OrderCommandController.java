package com.routemind.business.api.order;

import com.routemind.business.application.order.OrderCommandAuthorizationException;
import com.routemind.business.application.order.OrderCommandConflictException;
import com.routemind.business.application.order.OrderCommandResult;
import com.routemind.business.application.order.OrderCommandService;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import java.util.Locale;
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MissingRequestHeaderException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/orders")
public final class OrderCommandController {

	private static final Pattern TRACE_ID = Pattern.compile("[0-9a-f]{32}");
	private final OrderCommandService service;

	public OrderCommandController(OrderCommandService service) {
		this.service = service;
	}

	@PostMapping
	public ResponseEntity<OrderCommandResponse> create(@RequestHeader("Idempotency-Key") String idempotencyKey,
			@RequestHeader("X-Actor") String actor, @RequestHeader(value = "X-Correlation-Id", required = false)
			String correlationId, @RequestBody(required = false) CreateOrderRequest ignored) {
		OrderCommandResult result = service.create(normalizeActor(actor), correlation(correlationId), null, traceId(),
				idempotencyKey);
		return ResponseEntity.status(result.replayed() ? HttpStatus.OK : HttpStatus.CREATED)
			.body(OrderCommandResponse.from(result));
	}

	@PostMapping("/{orderId}/transitions")
	public OrderCommandResponse transition(@PathVariable UUID orderId,
			@RequestHeader("Idempotency-Key") String idempotencyKey, @RequestHeader("X-Actor") String actor,
			@RequestHeader(value = "X-Correlation-Id", required = false) String correlationId,
			@RequestBody TransitionRequest request) {
		if (request == null) {
			throw new IllegalArgumentException("transition request is required");
		}
		OrderStatus target = parseStatus(request.target());
		OrderCommandResult result = service.transitionCommand(new OrderId(orderId), target, normalizeActor(actor),
				request.expectedVersion(), correlation(correlationId), null, traceId(), idempotencyKey);
		return OrderCommandResponse.from(result);
	}

	@ExceptionHandler(OrderCommandAuthorizationException.class)
	ResponseEntity<ErrorResponse> forbidden(OrderCommandAuthorizationException exception) {
		return error(HttpStatus.FORBIDDEN, exception.getMessage());
	}

	@ExceptionHandler(OrderCommandConflictException.class)
	ResponseEntity<ErrorResponse> conflict(OrderCommandConflictException exception) {
		return error(HttpStatus.CONFLICT, exception.getMessage());
	}

	@ExceptionHandler(java.util.NoSuchElementException.class)
	ResponseEntity<ErrorResponse> notFound() {
		return error(HttpStatus.NOT_FOUND, "order_not_found");
	}

	@ExceptionHandler(IllegalStateException.class)
	ResponseEntity<ErrorResponse> invalidTransition(IllegalStateException exception) {
		return error(HttpStatus.CONFLICT, "invalid_transition");
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
		if (actor == null || actor.isBlank()) {
			throw new IllegalArgumentException("actor is required");
		}
		return actor.trim().toLowerCase(Locale.ROOT);
	}

	private static UUID correlation(String value) {
		return value == null || value.isBlank() ? UUID.randomUUID() : UUID.fromString(value);
	}

	private static String traceId() {
		String value = MDC.get("trace_id");
		return value != null && TRACE_ID.matcher(value).matches() ? value : "00000000000000000000000000000000";
	}

	private static OrderStatus parseStatus(String target) {
		if (target == null || target.isBlank()) {
			throw new IllegalArgumentException("target is required");
		}
		return OrderStatus.valueOf(target.trim().toUpperCase(Locale.ROOT));
	}

	public record CreateOrderRequest(String ignored) {
	}

	public record TransitionRequest(String target, long expectedVersion) {
	}

	public record OrderCommandResponse(UUID orderId, String status, long version, boolean replayed) {
		static OrderCommandResponse from(OrderCommandResult result) {
			return new OrderCommandResponse(result.orderId(), result.status(), result.version(), result.replayed());
		}
	}

	public record ErrorResponse(String code, String traceId) {
	}
}
