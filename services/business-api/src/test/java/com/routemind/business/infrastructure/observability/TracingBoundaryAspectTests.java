package com.routemind.business.infrastructure.observability;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.routemind.business.domain.dispatch.DispatchAssignmentCommand;
import com.routemind.business.domain.event.EventEnvelope;
import io.micrometer.observation.tck.TestObservationRegistry;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.Signature;
import org.junit.jupiter.api.Test;

class TracingBoundaryAspectTests {

	@Test
	void recordsDatabaseMessagingAndDecisionBoundariesWithoutACollector() throws Throwable {
		TestObservationRegistry registry = TestObservationRegistry.create();
		TracingBoundaryAspect aspect = new TracingBoundaryAspect(registry);
		UUID orderId = UUID.randomUUID();
		UUID correlationId = UUID.randomUUID();
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "order.assigned", Instant.EPOCH,
				"business-api", orderId, 2, correlationId, null,
				"0123456789abcdef0123456789abcdef", Map.of("status", "ASSIGNED"));
		DispatchAssignmentCommand command = new DispatchAssignmentCommand("decision-214", "v1",
				UUID.randomUUID(), "risk-aware", "1.0.0", "0".repeat(64), "1".repeat(64),
				false, null, 1);

		assertThat(aspect.observeDatabase(joinPoint("findById", new Object[0]))).isEqualTo("done");
		assertThat(aspect.observeMessaging(joinPoint("publish", new Object[] { event }))).isEqualTo("done");
		assertThat(aspect.observeDecision(joinPoint("record", new Object[] { orderId, command }))).isEqualTo("done");

		registry.assertThat()
				.hasNumberOfObservationsEqualTo(3)
				.hasAnObservationWithAKeyValue("routemind.boundary", "database")
				.hasAnObservationWithAKeyValue("routemind.boundary", "messaging")
				.hasAnObservationWithAKeyValue("routemind.boundary", "decision")
				.hasAnObservationWithAKeyValue("routemind.event_id", event.eventId().toString())
				.hasAnObservationWithAKeyValue("routemind.order_id", orderId.toString())
				.hasAnObservationWithAKeyValue("routemind.correlation_id", correlationId.toString())
				.hasAnObservationWithAKeyValue("routemind.decision_id", "decision-214");
	}

	private static ProceedingJoinPoint joinPoint(String operation, Object[] arguments) throws Throwable {
		ProceedingJoinPoint joinPoint = mock(ProceedingJoinPoint.class);
		Signature signature = mock(Signature.class);
		when(signature.getName()).thenReturn(operation);
		when(signature.getDeclaringTypeName()).thenReturn("com.routemind.test.Boundary");
		when(joinPoint.getSignature()).thenReturn(signature);
		when(joinPoint.getArgs()).thenReturn(arguments);
		when(joinPoint.proceed()).thenReturn("done");
		return joinPoint;
	}
}
