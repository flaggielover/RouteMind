package com.routemind.business.infrastructure.persistence.reconciliation;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.routemind.business.application.reconciliation.ReconciliationReport;
import com.routemind.business.application.reconciliation.ReconciliationReportRepository;
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

	public JdbcReconciliationReportRepository(JdbcTemplate jdbc, ObjectMapper mapper) {
		this.jdbc = jdbc;
		this.mapper = mapper;
	}

	@Override
	@Transactional
	public void append(ReconciliationReport report) {
		String json = serialize(report);
		jdbc.update("""
				insert into routemind.reconciliation_runs
				(run_id, checked_at, status, repair_mode, violation_count, unavailable_count, report_digest, report_json)
				values (?, ?, ?, ?, ?, ?, ?, ?)
				""", statement -> {
			statement.setObject(1, report.runId());
			statement.setTimestamp(2, Timestamp.from(report.checkedAt()));
			statement.setString(3, report.status().name());
			statement.setString(4, report.repairMode());
			statement.setInt(5, report.violationCount());
			statement.setInt(6, report.unavailableCount());
			statement.setString(7, digest(json));
			statement.setString(8, json);
		});
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<ReconciliationReport> findLatest() {
		List<String> reports = jdbc.queryForList("""
				select report_json from routemind.reconciliation_runs
				order by checked_at desc, run_id desc limit 1
				""", String.class);
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
