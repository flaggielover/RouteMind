package com.routemind.business.application.dispatch;

import com.routemind.business.application.order.OrderCommandResult;
import com.routemind.business.application.order.OrderCommandService;
import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import com.routemind.business.domain.dispatch.DispatchAssignmentCommand;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.order.OrderStatus;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DispatchAssignmentCommandService {

    private final OrderCommandService orders;
    private final DispatchAssignmentAuditRepository audits;
    private final OutboxRepository outbox;
    private final Clock clock;

    public DispatchAssignmentCommandService(OrderCommandService orders, DispatchAssignmentAuditRepository audits,
            OutboxRepository outbox, Clock clock) {
        this.orders = orders;
        this.audits = audits;
        this.outbox = outbox;
        this.clock = clock;
    }

    @Transactional
    public DispatchAssignmentResult apply(OrderId orderId, DispatchAssignmentCommand command,
            UUID correlationId, String traceId, String idempotencyKey) {
        String key = requireKey(idempotencyKey);
        String requestHash = fingerprint(orderId.value().toString(), command.requestId(), command.contractVersion(),
                command.courierId().toString(), command.strategy(), command.strategyVersion(), command.inputDigest(),
                command.outputDigest(), Boolean.toString(command.fallbackUsed()),
                command.fallbackReason() == null ? "" : command.fallbackReason(),
                Long.toString(command.expectedOrderVersion()));
        DispatchAssignmentAudit existing = audits.findByIdempotencyKey(key).orElse(null);
        if (existing != null) {
            if (!existing.requestHash().equals(requestHash)) throw new DispatchAssignmentConflictException("idempotency_key_reused");
            return new DispatchAssignmentResult(existing.orderId(), existing.courierId(), OrderStatus.ASSIGNED.name(),
                    existing.appliedOrderVersion(), true, existing);
        }

        OrderCommandResult transition = orders.transitionCommand(orderId, OrderStatus.ASSIGNED, "dispatch",
                command.expectedOrderVersion(), correlationId, null, traceId, key);
        DispatchAssignmentAudit audit = new DispatchAssignmentAudit(key, requestHash, command.requestId(),
                orderId.value(), command.courierId(), command.contractVersion(), command.strategy(),
                command.strategyVersion(), command.inputDigest(), command.outputDigest(), traceId,
                command.fallbackUsed(), command.fallbackReason(), transition.version(), clock.instant());
        audits.save(audit);
        Map<String, Object> payload = new HashMap<>();
        payload.put("orderId", orderId.value().toString());
        payload.put("courierId", command.courierId().toString());
        payload.put("requestId", command.requestId());
        payload.put("contractVersion", command.contractVersion());
        payload.put("strategy", command.strategy());
        payload.put("strategyVersion", command.strategyVersion());
        payload.put("inputDigest", command.inputDigest());
        payload.put("outputDigest", command.outputDigest());
        payload.put("fallbackUsed", command.fallbackUsed());
        if (command.fallbackReason() != null && !command.fallbackReason().isBlank()) payload.put("fallbackReason", command.fallbackReason());
        outbox.save(OutboxMessage.pending(new EventEnvelope("1.0", UUID.randomUUID(),
                "dispatch.assignment.applied", clock.instant(), "business-api", orderId.value(), transition.version(),
                correlationId, null, traceId, payload)));
        return new DispatchAssignmentResult(orderId.value(), command.courierId(), transition.status(),
                transition.version(), transition.replayed(), audit);
    }

    private static String requireKey(String key) {
        if (key == null || key.isBlank() || key.length() > 128 || key.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException("idempotency key is invalid");
        }
        return key.trim();
    }

    private static String fingerprint(String... fields) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (String field : fields) {
                byte[] bytes = field.getBytes(StandardCharsets.UTF_8);
                digest.update(Integer.toString(bytes.length).getBytes(StandardCharsets.US_ASCII));
                digest.update((byte) ':');
                digest.update(bytes);
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
