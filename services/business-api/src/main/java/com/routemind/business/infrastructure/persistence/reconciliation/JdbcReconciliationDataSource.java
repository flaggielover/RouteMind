package com.routemind.business.infrastructure.persistence.reconciliation;

import com.routemind.business.application.reconciliation.InvariantScan;
import com.routemind.business.application.reconciliation.ReconciliationDataSource;
import com.routemind.business.application.reconciliation.ReconciliationViolation;
import com.routemind.business.application.security.TenantContext;
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
	private final TenantContext tenants;

	public JdbcReconciliationDataSource(JdbcTemplate jdbc, TenantContext tenants) {
		this.jdbc = jdbc;
		this.tenants = tenants;
	}

	@Override
	@Transactional(readOnly = true)
	public InvariantScan inspectLeaseAssignments(Instant checkedAt) {
		UUID tenantId = tenants.current().value();
		List<ReconciliationViolation> violations = new ArrayList<>();
		violations.addAll(queryTenant("""
				select o.id as entity_id, o.status as order_status
				from routemind.orders o
				left join routemind.dispatch_assignment_leases l
				  on l.order_id = o.id and l.tenant_id = o.tenant_id and l.state = 'COMMITTED'
				where o.tenant_id = ? and o.status in ('ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP')
				group by o.id, o.status
				having count(l.courier_id) <> 1
				limit 100
				""", tenantId, "ASSIGNED_ORDER_LEASE_COUNT", "order", "order_status"));
		violations.addAll(queryTenant("""
				select l.lease_id as entity_id, l.state as lease_state, o.status as order_status
				from routemind.dispatch_assignment_leases l
				join routemind.orders o on o.id = l.order_id and o.tenant_id = l.tenant_id
				where l.tenant_id = ? and l.state = 'COMMITTED'
				  and o.status not in ('ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP')
				limit 100
				""", tenantId, "COMMITTED_LEASE_ORDER_STATE_MISMATCH", "lease", "lease_state", "order_status"));
		violations.addAll(queryTenant("""
				select l.lease_id as entity_id, l.decision_id, l.generation
				from routemind.dispatch_assignment_leases l
				left join routemind.dispatch_assignment_audits a
				  on a.lease_id = l.lease_id
				 and a.tenant_id = l.tenant_id
				 and a.lease_generation = l.generation
				 and a.order_id = l.order_id
				 and a.courier_id = l.courier_id
				 and a.request_id = l.decision_id
				where l.tenant_id = ? and l.state = 'COMMITTED' and a.idempotency_key is null
				limit 100
				""", tenantId, "COMMITTED_LEASE_AUDIT_MISMATCH", "lease", "decision_id", "generation"));
		violations.addAll(jdbc.query("""
				select lease_id as entity_id, decision_id, expires_at
				from routemind.dispatch_assignment_leases
				where tenant_id = ? and state = 'PROVISIONALLY_RESERVED' and expires_at <= ?
				limit 100
				""", (result, row) -> violation("EXPIRED_PROVISIONAL_LEASE", "lease", result,
					"decision_id", "expires_at"), tenantId, checkedAt));
		long inspected = countTenant("select count(*) from routemind.dispatch_assignment_leases where tenant_id = ?", tenantId)
				+ countTenant("select count(*) from routemind.orders where tenant_id = ? and status in ('ASSIGNED', 'ACCEPTED', 'ARRIVED', 'PICKED_UP')", tenantId);
		return scan(inspected, violations);
	}

	@Override
	@Transactional(readOnly = true)
	public InvariantScan inspectTerminalOrders() {
		UUID tenantId = tenants.current().value();
		List<ReconciliationViolation> violations = queryTenant("""
				select o.id as entity_id, o.status as order_status, l.state as lease_state, l.lease_id
				from routemind.orders o
				join routemind.dispatch_assignment_leases l on l.order_id = o.id and l.tenant_id = o.tenant_id
				where o.tenant_id = ? and o.status in ('DELIVERED', 'CANCELLED')
				  and l.state in ('PROVISIONALLY_RESERVED', 'COMMITTED')
				limit 100
				""", tenantId, "TERMINAL_ORDER_ACTIVE_LEASE", "order", "order_status", "lease_state", "lease_id");
		return scan(countTenant("select count(*) from routemind.orders where tenant_id = ? and status in ('DELIVERED', 'CANCELLED')", tenantId), violations);
	}

	@Override
	@Transactional(readOnly = true)
	public InvariantScan inspectDecisionReferences() {
		UUID tenantId = tenants.current().value();
		List<ReconciliationViolation> violations = queryTenant("""
				select a.idempotency_key as entity_id, a.request_id, a.order_id, a.courier_id
				from routemind.dispatch_assignment_audits a
				left join routemind.dispatch_decision_ledger d on d.logical_decision_id = a.request_id and d.tenant_id = a.tenant_id
				where a.tenant_id = ? and (d.decision_id is null
				   or d.idempotency_key <> a.idempotency_key
				   or d.order_id <> a.order_id
				   or d.courier_id <> a.courier_id
				   or d.strategy <> a.strategy
				   or d.strategy_version <> a.strategy_version
				   or d.input_digest <> a.input_digest
				   or d.output_digest <> a.output_digest)
				limit 100
				""", tenantId, "ASSIGNMENT_DECISION_REFERENCE_MISMATCH", "assignment_audit",
				"request_id", "order_id", "courier_id");
		return scan(countTenant("select count(*) from routemind.dispatch_assignment_audits where tenant_id = ?", tenantId), violations);
	}

	@Override
	@Transactional(readOnly = true)
	public Set<UUID> durableCourierIds() {
		return new TreeSet<>(jdbc.query("select courier_id from routemind.courier_locations where tenant_id = ?",
				(result, row) -> result.getObject(1, UUID.class), tenants.current().value()));
	}

	private List<ReconciliationViolation> queryTenant(String sql, UUID tenantId, String code, String entityType,
			String... evidenceColumns) {
		return jdbc.query(sql, (result, row) -> violation(code, entityType, result, evidenceColumns), tenantId);
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

	private long countTenant(String sql, UUID tenantId) {
		Long value = jdbc.queryForObject(sql, Long.class, tenantId);
		return value == null ? 0 : value;
	}
}
