package com.routemind.business.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.application.dispatch.DispatchAssignmentAuditRepository;
import com.routemind.business.application.inbox.InboxRepository;
import com.routemind.business.application.order.OrderCommandResult;
import com.routemind.business.application.order.OrderCommandService;
import com.routemind.business.application.order.OrderRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.domain.dispatch.DispatchAssignmentAudit;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.inbox.InboxMessage;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import com.routemind.business.domain.security.TenantId;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import org.flywaydb.core.Flyway;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.init.ScriptUtils;
import org.springframework.core.io.ClassPathResource;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

@SpringBootTest
@ActiveProfiles("test")
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class TenantIsolationIntegrationTests {

	private static final TenantId TENANT_A = TenantId.parse("10000000-0000-0000-0000-000000000001");
	private static final TenantId TENANT_B = TenantId.parse("20000000-0000-0000-0000-000000000002");
	private static final String TRACE_ID = "0123456789abcdef0123456789abcdef";
	private static final String ISOLATED_DATABASE = "jdbc:h2:mem:tenant_isolation_context;MODE=PostgreSQL;"
			+ "DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1";

	@DynamicPropertySource
	static void useIsolatedDatabase(DynamicPropertyRegistry registry) {
		registry.add("spring.datasource.url", () -> ISOLATED_DATABASE);
	}

	@Autowired
	private TenantContext tenants;

	@Autowired
	private OrderCommandService commands;

	@Autowired
	private OrderRepository orders;

	@Autowired
	private DispatchAssignmentAuditRepository audits;

	@Autowired
	private InboxRepository inbox;

	@Autowired
	private JdbcTemplate jdbc;

	@Test
	void transactionsEventsIdempotencyAndAuditsRemainTenantScoped() {
		String key = "tenant-replay-" + UUID.randomUUID();
		OrderCommandResult resultA = create(TENANT_A, key);
		OrderCommandResult resultB = create(TENANT_B, key);

		assertThat(resultA.replayed()).isFalse();
		assertThat(resultB.replayed()).isFalse();
		assertThat(resultB.orderId()).isNotEqualTo(resultA.orderId());
		assertThat(create(TENANT_B, key)).isEqualTo(new OrderCommandResult(
				resultB.orderId(), resultB.status(), resultB.version(), true));

		try (TenantContext.Scope ignored = tenants.open(TENANT_B)) {
			assertThat(orders.findById(new OrderId(resultA.orderId()))).isEmpty();
			Order conflicting = Order.create(new OrderId(resultA.orderId()), Instant.parse("2026-08-25T00:00:00Z"));
			assertThatThrownBy(() -> orders.save(conflicting)).isInstanceOf(TenantIsolationException.class)
					.hasMessage("tenant_scope_violation");
		}

		saveAudit(TENANT_A, key, resultA.orderId());
		saveAudit(TENANT_B, key, resultB.orderId());
		try (TenantContext.Scope ignored = tenants.open(TENANT_A)) {
			assertThat(audits.findByIdempotencyKey(key)).get().extracting(DispatchAssignmentAudit::orderId)
					.isEqualTo(resultA.orderId());
		}
		try (TenantContext.Scope ignored = tenants.open(TENANT_B)) {
			assertThat(audits.findByIdempotencyKey(key)).get().extracting(DispatchAssignmentAudit::orderId)
					.isEqualTo(resultB.orderId());
		}

		assertThat(count("routemind.order_command_idempotency", key)).isEqualTo(2);
		assertThat(count("routemind.dispatch_assignment_audits", key)).isEqualTo(2);
		assertThat(jdbc.queryForList("""
				select distinct tenant_id from routemind.outbox_messages
				where aggregate_id in (?, ?)
				""", UUID.class, resultA.orderId(), resultB.orderId()))
				.containsExactlyInAnyOrder(TENANT_A.value(), TENANT_B.value());
	}

	@Test
	void sameLogicalReplayKeyCanExecuteConcurrentlyWithoutCrossTenantReplay() throws Exception {
		String key = "tenant-concurrent-" + UUID.randomUUID();
		var executor = Executors.newFixedThreadPool(2);
		try {
			List<Callable<OrderCommandResult>> work = List.of(
					() -> create(TENANT_A, key),
					() -> create(TENANT_B, key));
			var futures = executor.invokeAll(work);
			OrderCommandResult left = futures.get(0).get();
			OrderCommandResult right = futures.get(1).get();
			assertThat(left.replayed()).isFalse();
			assertThat(right.replayed()).isFalse();
			assertThat(left.orderId()).isNotEqualTo(right.orderId());
		}
		finally {
			executor.shutdownNow();
		}
		assertThat(count("routemind.order_command_idempotency", key)).isEqualTo(2);
	}

	@Test
	void duplicateEventIdCannotBeReplayedIntoAnotherTenant() {
		UUID eventId = UUID.randomUUID();
		UUID aggregateId = UUID.randomUUID();
		Instant now = Instant.parse("2026-08-25T00:00:00Z");
		EventEnvelope tenantAEvent = event(eventId, aggregateId, TENANT_A, now);
		EventEnvelope tenantBReplay = event(eventId, aggregateId, TENANT_B, now);

		try (TenantContext.Scope ignored = tenants.open(TENANT_A)) {
			inbox.save(InboxMessage.received(tenantAEvent, now));
			assertThat(inbox.findById(eventId)).isPresent();
		}
		try (TenantContext.Scope ignored = tenants.open(TENANT_B)) {
			assertThat(inbox.findById(eventId)).isEmpty();
			assertThatThrownBy(() -> inbox.save(InboxMessage.received(tenantBReplay, now)))
					.isInstanceOf(TenantIsolationException.class)
					.hasMessage("tenant_scope_violation");
			assertThatThrownBy(() -> inbox.save(InboxMessage.received(tenantAEvent, now)))
					.isInstanceOf(TenantIsolationException.class)
					.hasMessage("tenant_scope_violation");
		}
	}

	@Test
	void v16BackfillsLegacyRowsAndMakesEveryDurableTableTenantAware() throws Exception {
		JdbcDataSource dataSource = new JdbcDataSource();
		dataSource.setURL("jdbc:h2:mem:tenant_migration_" + UUID.randomUUID()
				+ ";MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1");
		dataSource.setUser("sa");
		try (var anchor = dataSource.getConnection()) {
		Flyway.configure().dataSource(dataSource).createSchemas(true).schemas("routemind")
				.defaultSchema("routemind").target("15").load().migrate();
		JdbcTemplate migrationJdbc = new JdbcTemplate(dataSource);
		UUID orderId = UUID.randomUUID();
		migrationJdbc.update("""
				insert into routemind.order_command_idempotency
				(idempotency_key, request_hash, operation, order_id, response_status, response_version, created_at)
				values ('legacy-key', ?, 'create', ?, 'CREATED', 0, current_timestamp)
				""", "a".repeat(64), orderId);

		Flyway.configure().dataSource(dataSource).createSchemas(true).schemas("routemind")
				.defaultSchema("routemind").load().migrate();

		assertThat(migrationJdbc.queryForObject("""
				select tenant_id from routemind.order_command_idempotency where idempotency_key = 'legacy-key'
				""", UUID.class)).isEqualTo(TenantId.LEGACY.value());
		assertThat(migrationJdbc.queryForObject("""
				select logical_key from routemind.order_command_idempotency where idempotency_key = 'legacy-key'
				""", String.class)).isEqualTo("legacy-key");
		assertThat(migrationJdbc.queryForObject("""
				select count(*) from information_schema.columns
				where table_schema = 'routemind' and column_name = 'tenant_id'
				""", Integer.class)).isEqualTo(15);

		ScriptUtils.executeSqlScript(anchor,
				new ClassPathResource("db/rollback/U16__remove_tenant_isolation.sql"));
		assertThat(migrationJdbc.queryForObject("""
				select count(*) from information_schema.columns
				where table_schema = 'routemind' and column_name in ('tenant_id', 'logical_key',
				'logical_decision_id', 'logical_idempotency_key')
				""", Integer.class)).isZero();
		}
	}

	@Test
	void nestedTenantScopesRestoreAndClearTheirPreviousValue() {
		assertThatThrownBy(() -> TenantId.parse("1-1-1-1-1"))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("canonical");
		assertThat(tenants.current()).isEqualTo(TenantId.LEGACY);
		try (TenantContext.Scope ignored = tenants.open(TENANT_A)) {
			assertThat(tenants.current()).isEqualTo(TENANT_A);
			try (TenantContext.Scope nested = tenants.open(TENANT_B)) {
				assertThat(tenants.current()).isEqualTo(TENANT_B);
			}
			assertThat(tenants.current()).isEqualTo(TENANT_A);
		}
		assertThat(tenants.current()).isEqualTo(TenantId.LEGACY);
	}

	private OrderCommandResult create(TenantId tenant, String key) {
		try (TenantContext.Scope ignored = tenants.open(tenant)) {
			return commands.create("customer", UUID.randomUUID(), null, TRACE_ID, key);
		}
	}

	private void saveAudit(TenantId tenant, String key, UUID orderId) {
		try (TenantContext.Scope ignored = tenants.open(tenant)) {
			audits.save(new DispatchAssignmentAudit(key, "a".repeat(64), "request-" + tenant.value(),
					orderId, UUID.randomUUID(), "v1", "baseline", "1", "b".repeat(64),
					"c".repeat(64), TRACE_ID, false, null, 1, null, null, Instant.now()));
		}
	}

	private EventEnvelope event(UUID eventId, UUID aggregateId, TenantId tenant, Instant occurredAt) {
		return new EventEnvelope("1.0", eventId, "order.status.changed", occurredAt, "business-api",
				tenant.value(), aggregateId, 1, UUID.randomUUID(), null, TRACE_ID, java.util.Map.of());
	}

	private int count(String table, String logicalKey) {
		return jdbc.queryForObject("select count(*) from " + table + " where logical_key = ?", Integer.class,
				logicalKey);
	}
}
