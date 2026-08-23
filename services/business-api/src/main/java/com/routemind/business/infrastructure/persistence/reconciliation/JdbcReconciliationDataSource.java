package com.routemind.business.infrastructure.persistence.reconciliation;

import com.routemind.business.application.reconciliation.InvariantScan;
import com.routemind.business.application.reconciliation.ReconciliationDataSource;
import com.routemind.business.application.reconciliation.ReconciliationViolation;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JdbcReconciliationDataSource implements ReconciliationDataSource {

	private static final int EVIDENCE_LIMIT = 100;
	private final JdbcTemplate jdbc;

	public JdbcReconciliationDataSource(JdbcTemplate jdbc) {
		this.jdbc = jdbc;
	}

	@Override
	@Transactional(readOnly = true)
	public InvariantScan inspectLeaseAssignments(Instant checkedAt) {
		List<ReconciliationViolation> violations = new ArrayList<>();
		violations.addAll(query("""
				select o.id as entity_id, o.status as order_status
				from routemind.orders o
				left join routemind.dispatch_assignment_leases l
				  on l.order_id = o.id and l.state = 'COMMITTED'
				where o.status in ('ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP')
				group by o.id, o.status
				having count(l.courier_id) <> 1
				limit 100
				""", "ASSIGNED_ORDER_LEASE_COUNT", "order", "order_status"));
		violations.addAll(query("""
				select l.lease_id as entity_id, l.state as lease_state, o.status as order_status
				from routemind.dispatch_assignment_leases l
				join routemind.orders o on o.id = l.order_id
				where l.state = 'COMMITTED'
				  and o.status not in ('ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP')
				limit 100
				""", "COMMITTED_LEASE_ORDER_STATE_MISMATCH", "lease", "lease_state", "order_status"));
		violations.addAll(query("""
				select l.lease_id as entity_id, l.decision_id, l.generation
				from routemind.dispatch_assignment_leases l
				left join routemind.dispatch_assignment_audits a
				  on a.lease_id = l.lease_id
				 and a.lease_generation = l.generation
				 and a.order_id = l.order_id
				 and a.courier_id = l.courier_id
				 and a.request_id = l.decision_id
				where l.state = 'COMMITTED' and a.idempotency_key is null
				limit 100
				""", "COMMITTED_LEASE_AUDIT_MISMATCH", "lease", "decision_id", "generation"));
		violations.addAll(jdbc.query("""
				select lease_id as entity_id, decision_id, expires_at
				from routemind.dispatch_assignment_leases
				where state = 'PROVISIONALLY_RESERVED' and expires_at <= ?
				limit 100
				""", (result, row) -> violation("EXPIRED_PROVISIONAL_LEASE", "lease", result,
					"decision_id", "expires_at"), checkedAt));
		long inspected = count("select count(*) from routemind.dispatch_assignment_leases")
				+ count("select count(*) from routemind.orders where status in ('ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP')");
		return scan(inspected, violations);
	}

	@Override
	@Transactional(readOnly = true)
	public InvariantScan inspectTerminalOrders() {
		List<ReconciliationViolation> violations = query("""
				select o.id as entity_id, o.status as order_status, l.state as lease_state, l.lease_id
				from routemind.orders o
				join routemind.dispatch_assignment_leases l on l.order_id = o.id
				where o.status in ('DELIVERED', 'CANCELLED')
				  and l.state in ('PROVISIONALLY_RESERVED', 'COMMITTED')
				limit 100
				""", "TERMINAL_ORDER_ACTIVE_LEASE", "order", "order_status", "lease_state", "lease_id");
		return scan(count("select count(*) from routemind.orders where status in ('DELIVERED', 'CANCELLED')"), violations);
	}

	@Override
	@Transactional(readOnly = true)
	public InvariantScan inspectDecisionReferences() {
		List<ReconciliationViolation> violations = query("""
				select a.idempotency_key as entity_id, a.request_id, a.order_id, a.courier_id
				from routemind.dispatch_assignment_audits a
				left join routemind.dispatch_decision_ledger d on d.decision_id = a.request_id
				where d.decision_id is null
				   or d.idempotency_key <> a.idempotency_key
				   or d.order_id <> a.order_id
				   or d.courier_id <> a.courier_id
				   or d.strategy <> a.strategy
				   or d.strategy_version <> a.strategy_version
				   or d.input_digest <> a.input_digest
				   or d.output_digest <> a.output_digest
				limit 100
				""", "ASSIGNMENT_DECISION_REFERENCE_MISMATCH", "assignment_audit",
				"request_id", "order_id", "courier_id");
		return scan(count("select count(*) from routemind.dispatch_assignment_audits"), violations);
	}

	@Override
	@Transactional(readOnly = true)
	public Set<UUID> durableCourierIds() {
		return new TreeSet<>(jdbc.query("select courier_id from routemind.courier_locations",
				(result, row) -> result.getObject(1, UUID.class)));
	}

	private List<ReconciliationViolation> query(String sql, String code, String entityType,
			String... evidenceColumns) {
		return jdbc.query(sql, (result, row) -> violation(code, entityType, result, evidenceColumns));
	}

	private static ReconciliationViolation violation(String code, String entityType, ResultSet result,
			String... evidenceColumns) throws SQLException {
		Map<String, String> evidence = new LinkedHashMap<>();
		for (String column : evidenceColumns) {
			Object value = result.getObject(column);
			evidence.put(column, value == null ? "null" : value.toString());
		}
		return new ReconciliationViolation(code, entityType, result.getObject("entity_id").toString(), evidence);
	}

	private InvariantScan scan(long inspected, List<ReconciliationViolation> violations) {
		boolean truncated = violations.size() > EVIDENCE_LIMIT;
		List<ReconciliationViolation> bounded = violations.stream().limit(EVIDENCE_LIMIT).toList();
		return new InvariantScan(inspected, bounded, Map.of(
				"evidence_limit", Integer.toString(EVIDENCE_LIMIT),
				"evidence_truncated", Boolean.toString(truncated),
				"violations_returned", Integer.toString(bounded.size())));
	}

	private long count(String sql) {
		Long value = jdbc.queryForObject(sql, Long.class);
		return value == null ? 0 : value;
	}
}
