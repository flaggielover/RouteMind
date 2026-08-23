package com.routemind.business.api.dispatch;

import com.routemind.business.application.dispatch.DispatchAssignmentCommandService;
import com.routemind.business.application.dispatch.DispatchAssignmentConflictException;
import com.routemind.business.application.dispatch.DispatchAssignmentLeaseConflictException;
import com.routemind.business.application.dispatch.DispatchAssignmentResult;
import com.routemind.business.application.order.OrderCommandAuthorizationException;
import com.routemind.business.application.order.OrderCommandConflictException;
import com.routemind.business.domain.dispatch.DispatchAssignmentCommand;
import com.routemind.business.domain.order.OrderId;
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
@RequestMapping("/api/v1/orders")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public final class DispatchAssignmentController {

    private static final Pattern TRACE_ID = Pattern.compile("[0-9a-f]{32}");
    private final DispatchAssignmentCommandService assignments;

    public DispatchAssignmentController(DispatchAssignmentCommandService assignments) {
        this.assignments = assignments;
    }

    @PostMapping("/{orderId}/dispatch-assignment")
    public DispatchAssignmentResponse assign(@PathVariable UUID orderId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestHeader(value = "X-Correlation-Id", required = false) String correlationId,
            @RequestBody DispatchAssignmentRequest request) {
        if (request == null) throw new IllegalArgumentException("dispatch assignment request is required");
        DispatchAssignmentCommand command = new DispatchAssignmentCommand(request.requestId(), request.contractVersion(),
                request.courierId(), request.strategy(), request.strategyVersion(), request.inputDigest(),
                request.outputDigest(), request.fallbackUsed(), request.fallbackReason(), request.expectedOrderVersion());
        DispatchAssignmentResult result = assignments.apply(new OrderId(orderId), command, correlation(correlationId),
                traceId(), idempotencyKey);
        return DispatchAssignmentResponse.from(result, traceId());
    }

    @ExceptionHandler(DispatchAssignmentConflictException.class)
    ResponseEntity<ErrorResponse> conflict(DispatchAssignmentConflictException exception) {
        return error(HttpStatus.CONFLICT, exception.getMessage());
    }

    @ExceptionHandler(DispatchAssignmentLeaseConflictException.class)
    ResponseEntity<ErrorResponse> leaseConflict(DispatchAssignmentLeaseConflictException exception) {
        return error(HttpStatus.CONFLICT, exception.getMessage());
    }

    @ExceptionHandler(OrderCommandConflictException.class)
    ResponseEntity<ErrorResponse> stale(OrderCommandConflictException exception) {
        return error(HttpStatus.CONFLICT, exception.getMessage());
    }

    @ExceptionHandler(OrderCommandAuthorizationException.class)
    ResponseEntity<ErrorResponse> forbidden(OrderCommandAuthorizationException exception) {
        return error(HttpStatus.FORBIDDEN, exception.getMessage());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<ErrorResponse> invalidRequest(IllegalArgumentException exception) {
        return error(HttpStatus.BAD_REQUEST, exception.getMessage());
    }

    @ExceptionHandler(MissingRequestHeaderException.class)
    ResponseEntity<ErrorResponse> missingHeader(MissingRequestHeaderException exception) {
        return error(HttpStatus.BAD_REQUEST, "idempotency_key_required");
    }

    private ResponseEntity<ErrorResponse> error(HttpStatus status, String code) {
        return ResponseEntity.status(status).body(new ErrorResponse(code, traceId()));
    }

    private static UUID correlation(String value) {
        return value == null || value.isBlank() ? UUID.randomUUID() : UUID.fromString(value);
    }

    private static String traceId() {
        String value = MDC.get("trace_id");
        return value != null && TRACE_ID.matcher(value).matches() ? value : "00000000000000000000000000000000";
    }

    public record DispatchAssignmentRequest(String requestId, String contractVersion, UUID courierId,
            String strategy, String strategyVersion, String inputDigest, String outputDigest,
            boolean fallbackUsed, String fallbackReason, long expectedOrderVersion) {
    }

    public record DispatchAssignmentResponse(UUID orderId, UUID courierId, String status, long version,
            boolean replayed, String requestId, String contractVersion, String strategy, String strategyVersion,
            String inputDigest, String outputDigest, boolean fallbackUsed, String fallbackReason, UUID leaseId,
            Long leaseGeneration, String traceId) {
        static DispatchAssignmentResponse from(DispatchAssignmentResult result, String traceId) {
            var audit = result.audit();
            return new DispatchAssignmentResponse(result.orderId(), result.courierId(), result.status(), result.version(),
                    result.replayed(), audit.requestId(), audit.contractVersion(), audit.strategy(), audit.strategyVersion(),
                    audit.inputDigest(), audit.outputDigest(), audit.fallbackUsed(), audit.fallbackReason(), audit.leaseId(),
                    audit.leaseGeneration(), traceId);
        }
    }

    public record ErrorResponse(String code, String traceId) {
    }
}
