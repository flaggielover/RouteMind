package com.routemind.business.application.dispatch;

import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import java.util.Optional;

public interface DispatchAssignmentAuditRepository {

    DispatchAssignmentAudit save(DispatchAssignmentAudit audit);

    Optional<DispatchAssignmentAudit> findByIdempotencyKey(String idempotencyKey);
}
