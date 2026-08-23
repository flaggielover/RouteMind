package com.routemind.business.infrastructure.reconciliation;

import com.routemind.business.application.reconciliation.ReconciliationReport;
import com.routemind.business.application.reconciliation.ReconciliationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "routemind.reconciliation.scheduler.enabled", havingValue = "true", matchIfMissing = true)
public class ReconciliationScheduler {

	private static final Logger LOGGER = LoggerFactory.getLogger(ReconciliationScheduler.class);
	private final ReconciliationService service;

	public ReconciliationScheduler(ReconciliationService service) {
		this.service = service;
	}

	@Scheduled(initialDelayString = "${routemind.reconciliation.scheduler.initial-delay-ms:30000}",
			fixedDelayString = "${routemind.reconciliation.scheduler.fixed-delay-ms:60000}")
	public void reconcile() {
		ReconciliationReport report = service.runDetectOnly();
		LOGGER.atInfo()
				.addKeyValue("event", "reconciliation_completed")
				.addKeyValue("run_id", report.runId())
				.addKeyValue("status", report.status())
				.addKeyValue("violations", report.violationCount())
				.addKeyValue("unavailable", report.unavailableCount())
				.log("Detect-only reconciliation completed");
	}
}
