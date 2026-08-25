package com.routemind.business.infrastructure.persistence.reconciliation;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.reconciliation.ReconciliationReport;
import com.routemind.business.application.reconciliation.ReconciliationReportRepository;
import com.routemind.business.application.security.TenantContext;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Timestamp;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JdbcReconciliationReportRepository implements ReconciliationReportRepository {

	private final JdbcTemplate jdbc;
	private final ObjectMapper mapper;
	private final TenantContext tenants;

	public JdbcReconciliationReportRepository(JdbcTemplate jdbc, ObjectMapper mapper, TenantContext tenants) {
		this.jdbc = jdbc;
		this.mapper = mapper;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public void append(ReconciliationReport report) {
		String json = serialize(report);
		jdbc.update("""
				insert into routemind.reconciliation_runs
				(tenant_id, run_id, checked_at, status, repair_mode, violation_count, unavailable_count, report_digest, report_json)
				values (?, ?, ?, ?, ?, ?, ?, ?, ?)
				""", statement -> {
			statement.setObject(1, tenants.current().value());
			statement.setObject(2, report.runId());
			statement.setTimestamp(3, Timestamp.from(report.checkedAt()));
			statement.setString(4, report.status().name());
			statement.setString(5, report.repairMode());
			statement.setInt(6, report.violationCount());
			statement.setInt(7, report.unavailableCount());
			statement.setString(8, digest(json));
			statement.setString(9, json);
		});
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<ReconciliationReport> findLatest() {
		List<String> reports = jdbc.queryForList("""
				select report_json from routemind.reconciliation_runs
				where tenant_id = ? order by checked_at desc, run_id desc limit 1
				""", String.class, tenants.current().value());
		return reports.stream().findFirst().map(this::deserialize);
	}

	private String serialize(ReconciliationReport report) {
		try {
			return mapper.writeValueAsString(report);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalStateException("reconciliation report cannot be serialized", exception);
		}
	}

	private ReconciliationReport deserialize(String json) {
		try {
			return mapper.readValue(json, ReconciliationReport.class);
		}
		catch (JsonProcessingException exception) {
			throw new IllegalStateException("stored reconciliation report is invalid", exception);
		}
	}

	private static String digest(String json) {
		try {
			return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
					.digest(json.getBytes(StandardCharsets.UTF_8)));
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}
}
