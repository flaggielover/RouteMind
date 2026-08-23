package com.routemind.business.application.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import java.util.UUID;

public record DispatchAssignmentResult(UUID orderId, UUID courierId, String status, long version,
        boolean replayed, DispatchAssignmentAudit audit) {
}
