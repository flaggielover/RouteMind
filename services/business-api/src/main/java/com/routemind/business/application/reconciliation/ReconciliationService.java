package com.routemind.business.application.reconciliation;

import com.routemind.business.application.courier.CourierGeoProjection;
import com.routemind.business.application.courier.CourierProjectionInspection;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class ReconciliationService {

	private static final int EVIDENCE_LIMIT = 100;
	private static final Logger LOGGER = LoggerFactory.getLogger(ReconciliationService.class);
	private final ReconciliationDataSource dataSource;
	private final ReconciliationReportRepository reports;
	private final CourierGeoProjection projection;
	private final Clock clock;
	private final AtomicReference<ReconciliationReport> latest = new AtomicReference<>();

	public ReconciliationService(ReconciliationDataSource dataSource, ReconciliationReportRepository reports,
			CourierGeoProjection projection, Clock clock) {
		this.dataSource = dataSource;
		this.reports = reports;
		this.projection = projection;
		this.clock = clock;
	}

	public synchronized ReconciliationReport runDetectOnly() {
		Instant checkedAt = clock.instant();
		List<ReconciliationCheck> checks = new ArrayList<>();
		checks.add(scan("lease_assignment", () -> dataSource.inspectLeaseAssignments(checkedAt)));
		checks.add(scan("terminal_order", dataSource::inspectTerminalOrders));
		checks.add(scan("decision_reference", dataSource::inspectDecisionReferences));
		checks.add(inspectProjection());
		checks.add(new ReconciliationCheck("evidence_store", ReconciliationCheck.Status.PASS, 1, List.of(),
				Map.of("storage", "postgresql", "mode", "append_only")));
		UUID runId = UUID.randomUUID();
		ReconciliationReport report = report(runId, checkedAt, checks);
		try {
			reports.append(report);
		}
		catch (RuntimeException failure) {
			LOGGER.warn("Reconciliation evidence append failed run_id={}", runId, failure);
			checks.set(checks.size() - 1, unavailable("evidence_store", "append_failed", failure));
			report = report(runId, checkedAt, checks);
		}
		latest.set(report);
		return report;
	}

	public Optional<ReconciliationReport> latest() {
		ReconciliationReport current = latest.get();
		if (current != null) return Optional.of(current);
		try {
			Optional<ReconciliationReport> stored = reports.findLatest();
			stored.ifPresent(latest::set);
			return stored;
		}
		catch (RuntimeException ignored) {
			return Optional.empty();
		}
	}

	private ReconciliationCheck scan(String name, Supplier<InvariantScan> operation) {
		try {
			InvariantScan scan = operation.get();
			ReconciliationCheck.Status status = scan.violations().isEmpty()
					? ReconciliationCheck.Status.PASS : ReconciliationCheck.Status.FAIL;
			return new ReconciliationCheck(name, status, scan.inspectedCount(), scan.violations(), scan.evidence());
		}
		catch (RuntimeException failure) {
			return unavailable(name, "durable_query_failed", failure);
		}
	}

	private ReconciliationCheck inspectProjection() {
		final Set<UUID> durableIds;
		try {
			durableIds = dataSource.durableCourierIds();
		}
		catch (RuntimeException failure) {
			return unavailable("courier_projection", "durable_location_query_failed", failure);
		}
		final CourierProjectionInspection inspection;
		try {
			inspection = projection.inspect();
		}
		catch (RuntimeException failure) {
			return unavailable("courier_projection", "projection_inspection_failed", failure);
		}
		if (inspection.status() == CourierProjectionInspection.Status.UNAVAILABLE) {
			return new ReconciliationCheck("courier_projection", ReconciliationCheck.Status.UNAVAILABLE,
					durableIds.size(), List.of(), inspection.evidence());
		}
		List<ReconciliationViolation> violations = new ArrayList<>();
		long missingCount = durableIds.stream().filter(id -> !inspection.courierIds().contains(id)).count();
		long orphanedCount = inspection.courierIds().stream().filter(id -> !durableIds.contains(id)).count();
		durableIds.stream().filter(id -> !inspection.courierIds().contains(id)).sorted().limit(EVIDENCE_LIMIT)
				.map(id -> new ReconciliationViolation("DURABLE_COURIER_MISSING_FROM_PROJECTION", "courier",
						id.toString(), Map.of("durable", "true", "projected", "false")))
				.forEach(violations::add);
		inspection.courierIds().stream().filter(id -> !durableIds.contains(id)).sorted()
				.limit(EVIDENCE_LIMIT - violations.size())
				.map(id -> new ReconciliationViolation("ORPHANED_PROJECTION_COURIER", "courier",
						id.toString(), Map.of("durable", "false", "projected", "true")))
				.forEach(violations::add);
		Map<String, String> evidence = new LinkedHashMap<>(inspection.evidence());
		evidence.put("durable_count", Integer.toString(durableIds.size()));
		evidence.put("projection_count", Integer.toString(inspection.courierIds().size()));
		evidence.put("missing_count", Long.toString(missingCount));
		evidence.put("orphaned_count", Long.toString(orphanedCount));
		evidence.put("evidence_limit", Integer.toString(EVIDENCE_LIMIT));
		evidence.put("evidence_truncated", Boolean.toString(missingCount + orphanedCount > EVIDENCE_LIMIT));
		return new ReconciliationCheck("courier_projection", violations.isEmpty()
				? ReconciliationCheck.Status.PASS : ReconciliationCheck.Status.FAIL,
				Math.max(durableIds.size(), inspection.courierIds().size()), violations, evidence);
	}

	private static ReconciliationReport report(UUID runId, Instant checkedAt, List<ReconciliationCheck> checks) {
		int violationCount = checks.stream().mapToInt(check -> check.violations().size()).sum();
		int unavailableCount = (int) checks.stream()
				.filter(check -> check.status() == ReconciliationCheck.Status.UNAVAILABLE).count();
		ReconciliationReport.Status status = violationCount > 0
				? ReconciliationReport.Status.DRIFT_DETECTED
				: unavailableCount > 0 ? ReconciliationReport.Status.DEGRADED : ReconciliationReport.Status.HEALTHY;
		return new ReconciliationReport(runId, checkedAt, status, "DETECT_ONLY", violationCount,
				unavailableCount, checks);
	}

	private static ReconciliationCheck unavailable(String name, String reason, RuntimeException failure) {
		return new ReconciliationCheck(name, ReconciliationCheck.Status.UNAVAILABLE, 0, List.of(),
				Map.of("reason", reason, "failure_type", failure.getClass().getSimpleName()));
	}
}
