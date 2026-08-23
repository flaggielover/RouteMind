package com.routemind.business.application.dispatch;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.routemind.business.application.order.OrderCommandResult;
import com.routemind.business.domain.dispatch.DispatchAssignmentCommand;
import com.routemind.business.domain.dispatch.DispatchAssignmentLease;
import com.routemind.business.domain.dispatch.DispatchDecisionLedger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.Map;
import java.util.TreeMap;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DispatchDecisionLedgerService {

    private static final String REFERENCE_DATA_ID = "dispatch-api:v1";
    private final DispatchDecisionLedgerRepository ledgers;
    private final ObjectMapper mapper;
    private final Clock clock;

    public DispatchDecisionLedgerService(DispatchDecisionLedgerRepository ledgers, ObjectMapper mapper, Clock clock) {
        this.ledgers = ledgers;
        this.mapper = mapper.copy().configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
        this.clock = clock;
    }

    @Transactional
    public DispatchDecisionLedger record(UUID orderId, DispatchAssignmentCommand command, String idempotencyKey,
            DispatchAssignmentLease lease, OrderCommandResult transition) {
        String inputSnapshot = snapshot(input(orderId, command));
        String outputSnapshot = snapshot(output(orderId, command, lease, transition));
        DispatchDecisionLedger candidate = new DispatchDecisionLedger(command.requestId(), command.requestId(),
                idempotencyKey, orderId, command.courierId(), command.strategy(), command.strategyVersion(),
                REFERENCE_DATA_ID, "WALL", command.inputDigest(), command.outputDigest(), digest(inputSnapshot),
                digest(outputSnapshot), inputSnapshot, outputSnapshot, clock.instant());
        DispatchDecisionLedger existing = ledgers.findByDecisionId(candidate.decisionId()).orElse(null);
        if (existing != null) {
            if (!existing.inputDigest().equals(candidate.inputDigest())
                    || !existing.outputDigest().equals(candidate.outputDigest())
                    || !existing.orderId().equals(candidate.orderId())) {
                throw new DispatchAssignmentConflictException("decision_id_reused");
            }
            return existing;
        }
        return ledgers.save(candidate);
    }

    private static Map<String, Object> input(UUID orderId, DispatchAssignmentCommand command) {
        Map<String, Object> values = new TreeMap<>();
        values.put("clock_domain", "WALL");
        values.put("contract_version", command.contractVersion());
        values.put("courier_id", command.courierId().toString());
        values.put("expected_order_version", command.expectedOrderVersion());
        values.put("fallback_reason", command.fallbackReason());
        values.put("fallback_used", command.fallbackUsed());
        values.put("input_digest", command.inputDigest());
        values.put("order_id", orderId.toString());
        values.put("reference_data_id", REFERENCE_DATA_ID);
        values.put("request_id", command.requestId());
        values.put("strategy", command.strategy());
        values.put("strategy_version", command.strategyVersion());
        return values;
    }

    private static Map<String, Object> output(UUID orderId, DispatchAssignmentCommand command,
            DispatchAssignmentLease lease, OrderCommandResult transition) {
        Map<String, Object> values = new TreeMap<>();
        values.put("clock_domain", "WALL");
        values.put("courier_id", command.courierId().toString());
        values.put("lease_generation", lease.generation());
        values.put("lease_id", lease.leaseId().toString());
        values.put("order_id", orderId.toString());
        values.put("output_digest", command.outputDigest());
        values.put("status", transition.status());
        values.put("strategy", command.strategy());
        values.put("strategy_version", command.strategyVersion());
        values.put("version", transition.version());
        return values;
    }

    private String snapshot(Map<String, Object> values) {
        try {
            return mapper.writeValueAsString(values);
        }
        catch (JsonProcessingException exception) {
            throw new IllegalStateException("dispatch ledger snapshot cannot be serialized", exception);
        }
    }

    private static String digest(String value) {
        try {
            return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        }
        catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
