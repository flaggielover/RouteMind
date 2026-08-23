package com.routemind.business.application.reconciliation;

import java.time.Instant;
import java.util.Set;
import java.util.UUID;

public interface ReconciliationDataSource {

	InvariantScan inspectLeaseAssignments(Instant checkedAt);

	InvariantScan inspectTerminalOrders();

	InvariantScan inspectDecisionReferences();

	Set<UUID> durableCourierIds();
}
