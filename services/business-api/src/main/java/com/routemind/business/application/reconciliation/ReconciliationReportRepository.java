package com.routemind.business.application.reconciliation;

import java.util.Optional;

public interface ReconciliationReportRepository {

	void append(ReconciliationReport report);

	Optional<ReconciliationReport> findLatest();
}
