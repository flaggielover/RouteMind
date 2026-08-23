package com.routemind.business.application.reconciliation;

import static org.assertj.core.api.Assertions.assertThat;

import com.routemind.business.application.courier.CourierGeoProjection;
import com.routemind.business.application.courier.CourierProjectionInspection;
import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.NearbyCourier;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ReconciliationServiceTests {

	private static final Instant CHECKED_AT = Instant.parse("2026-08-23T12:00:00Z");
	private static final UUID COURIER_ID = UUID.fromString("10000000-0000-0000-0000-000000000001");

	@Test
	void recordsHealthyDetectOnlyEvidenceWhenAllInvariantsAgree() {
		MemoryReports reports = new MemoryReports(false);
		ReconciliationService service = service(healthyDataSource(), availableProjection(Set.of(COURIER_ID)), reports);

		ReconciliationReport report = service.runDetectOnly();

		assertThat(report.status()).isEqualTo(ReconciliationReport.Status.HEALTHY);
		assertThat(report.repairMode()).isEqualTo("DETECT_ONLY");
		assertThat(report.violationCount()).isZero();
		assertThat(report.unavailableCount()).isZero();
		assertThat(report.checkedAt()).isEqualTo(CHECKED_AT);
		assertThat(report.checks()).extracting(ReconciliationCheck::name)
				.containsExactly("lease_assignment", "terminal_order", "decision_reference",
						"courier_projection", "evidence_store");
		assertThat(report.checks()).allMatch(check -> check.status() == ReconciliationCheck.Status.PASS);
		assertThat(reports.latest).contains(report);
		assertThat(service.latest()).contains(report);
	}

	@Test
	void reportsDriftAndUnavailableProjectionWithoutAttemptingRepair() {
		ReconciliationViolation violation = new ReconciliationViolation("COMMITTED_LEASE_ORDER_STATE_MISMATCH",
				"lease", "lease-1", Map.of("lease_state", "COMMITTED", "order_status", "CANCELLED"));
		ReconciliationDataSource source = dataSource(new InvariantScan(2, List.of(violation), Map.of()),
				emptyScan(), emptyScan(), Set.of(COURIER_ID));
		ReconciliationService service = service(source,
				projection(CourierProjectionInspection.unavailable("redis_unavailable")), new MemoryReports(false));

		ReconciliationReport report = service.runDetectOnly();

		assertThat(report.status()).isEqualTo(ReconciliationReport.Status.DRIFT_DETECTED);
		assertThat(report.violationCount()).isOne();
		assertThat(report.unavailableCount()).isOne();
		assertThat(report.checks()).filteredOn(check -> check.name().equals("lease_assignment"))
				.singleElement().satisfies(check -> {
					assertThat(check.status()).isEqualTo(ReconciliationCheck.Status.FAIL);
					assertThat(check.violations()).containsExactly(violation);
				});
		assertThat(report.checks()).filteredOn(check -> check.name().equals("courier_projection"))
				.singleElement().satisfies(check ->
						assertThat(check.status()).isEqualTo(ReconciliationCheck.Status.UNAVAILABLE));
		assertThat(report.repairMode()).isEqualTo("DETECT_ONLY");
	}

	@Test
	void degradesWhenAQueryOrEvidenceAppendFailsInsteadOfClaimingHealthy() {
		ReconciliationDataSource source = new ReconciliationDataSource() {
			@Override
			public InvariantScan inspectLeaseAssignments(Instant checkedAt) {
				throw new IllegalStateException("database unavailable");
			}

			@Override
			public InvariantScan inspectTerminalOrders() {
				return emptyScan();
			}

			@Override
			public InvariantScan inspectDecisionReferences() {
				return emptyScan();
			}

			@Override
			public Set<UUID> durableCourierIds() {
				return Set.of();
			}
		};
		ReconciliationService service = service(source, availableProjection(Set.of()), new MemoryReports(true));

		ReconciliationReport report = service.runDetectOnly();

		assertThat(report.status()).isEqualTo(ReconciliationReport.Status.DEGRADED);
		assertThat(report.unavailableCount()).isEqualTo(2);
		assertThat(report.checks()).filteredOn(check -> check.status() == ReconciliationCheck.Status.UNAVAILABLE)
				.extracting(ReconciliationCheck::name).containsExactly("lease_assignment", "evidence_store");
		assertThat(service.latest()).contains(report);
	}

	@Test
	void detectsMissingAndOrphanedProjectionMembers() {
		UUID orphaned = UUID.fromString("20000000-0000-0000-0000-000000000002");
		ReconciliationService service = service(healthyDataSource(), availableProjection(Set.of(orphaned)),
				new MemoryReports(false));

		ReconciliationReport report = service.runDetectOnly();

		assertThat(report.status()).isEqualTo(ReconciliationReport.Status.DRIFT_DETECTED);
		assertThat(report.violationCount()).isEqualTo(2);
		assertThat(report.checks()).filteredOn(check -> check.name().equals("courier_projection"))
				.singleElement().satisfies(check -> assertThat(check.violations())
						.extracting(ReconciliationViolation::code)
						.containsExactlyInAnyOrder("DURABLE_COURIER_MISSING_FROM_PROJECTION",
								"ORPHANED_PROJECTION_COURIER"));
	}

	@Test
	void boundsCombinedProjectionEvidenceAndRetainsTotalCounts() {
		Set<UUID> durable = java.util.stream.IntStream.rangeClosed(1, 101)
				.mapToObj(index -> new UUID(0, index)).collect(java.util.stream.Collectors.toSet());
		Set<UUID> projected = java.util.stream.IntStream.rangeClosed(1001, 1101)
				.mapToObj(index -> new UUID(0, index)).collect(java.util.stream.Collectors.toSet());
		ReconciliationDataSource source = dataSource(emptyScan(), emptyScan(), emptyScan(), durable);
		ReconciliationService service = service(source, availableProjection(projected), new MemoryReports(false));

		ReconciliationReport report = service.runDetectOnly();

		assertThat(report.violationCount()).isEqualTo(100);
		assertThat(report.checks()).filteredOn(check -> check.name().equals("courier_projection"))
				.singleElement().satisfies(check -> {
					assertThat(check.violations()).hasSize(100);
					assertThat(check.evidence()).containsEntry("missing_count", "101")
							.containsEntry("orphaned_count", "101")
							.containsEntry("evidence_truncated", "true");
				});
	}

	private static ReconciliationService service(ReconciliationDataSource source, CourierGeoProjection projection,
			MemoryReports reports) {
		return new ReconciliationService(source, reports, projection, Clock.fixed(CHECKED_AT, ZoneOffset.UTC));
	}

	private static ReconciliationDataSource healthyDataSource() {
		return dataSource(emptyScan(), emptyScan(), emptyScan(), Set.of(COURIER_ID));
	}

	private static ReconciliationDataSource dataSource(InvariantScan leases, InvariantScan terminal,
			InvariantScan decisions, Set<UUID> durableIds) {
		return new ReconciliationDataSource() {
			@Override
			public InvariantScan inspectLeaseAssignments(Instant checkedAt) {
				return leases;
			}

			@Override
			public InvariantScan inspectTerminalOrders() {
				return terminal;
			}

			@Override
			public InvariantScan inspectDecisionReferences() {
				return decisions;
			}

			@Override
			public Set<UUID> durableCourierIds() {
				return durableIds;
			}
		};
	}

	private static InvariantScan emptyScan() {
		return new InvariantScan(0, List.of(), Map.of());
	}

	private static CourierGeoProjection availableProjection(Set<UUID> courierIds) {
		return projection(new CourierProjectionInspection(CourierProjectionInspection.Status.AVAILABLE,
				courierIds, Map.of("provider", "test")));
	}

	private static CourierGeoProjection projection(CourierProjectionInspection inspection) {
		return new CourierGeoProjection() {
			@Override
			public void upsert(CourierLocation location) {
			}

			@Override
			public List<NearbyCourier> nearby(double latitude, double longitude, double radiusKilometers) {
				return List.of();
			}

			@Override
			public void rebuild(List<CourierLocation> locations) {
			}

			@Override
			public CourierProjectionInspection inspect() {
				return inspection;
			}
		};
	}

	private static final class MemoryReports implements ReconciliationReportRepository {
		private final boolean failAppend;
		private Optional<ReconciliationReport> latest = Optional.empty();

		private MemoryReports(boolean failAppend) {
			this.failAppend = failAppend;
		}

		@Override
		public void append(ReconciliationReport report) {
			if (failAppend) throw new IllegalStateException("evidence unavailable");
			latest = Optional.of(report);
		}

		@Override
		public Optional<ReconciliationReport> findLatest() {
			return latest;
		}
	}
}
