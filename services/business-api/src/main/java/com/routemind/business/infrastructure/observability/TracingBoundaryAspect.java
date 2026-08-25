package com.routemind.business.infrastructure.observability;

import com.routemind.business.domain.dispatch.DispatchAssignmentCommand;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.application.observability.TelemetryAttribution;
import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
public final class TracingBoundaryAspect {

	private final ObservationRegistry registry;
	private final TelemetryAttribution telemetry;

	public TracingBoundaryAspect(ObservationRegistry registry, TelemetryAttribution telemetry) {
		this.registry = registry;
		this.telemetry = telemetry;
	}

	@Around("execution(public * com.routemind.business.infrastructure.persistence..Jpa*.*(..))")
	public Object observeDatabase(ProceedingJoinPoint joinPoint) throws Throwable {
		Observation observation = Observation.createNotStarted("routemind.database", registry)
				.contextualName("database " + joinPoint.getSignature().getName())
				.lowCardinalityKeyValue("routemind.boundary", "database")
				.lowCardinalityKeyValue("db.system.name", "postgresql")
				.lowCardinalityKeyValue("db.operation.name", joinPoint.getSignature().getName())
				.lowCardinalityKeyValue("code.namespace", joinPoint.getSignature().getDeclaringTypeName());
		return proceed(joinPoint, observation);
	}

	@Around("execution(public * com.routemind.business.infrastructure.outbox.RabbitOutboxPublisher.publish(..))")
	public Object observeMessaging(ProceedingJoinPoint joinPoint) throws Throwable {
		Observation observation = Observation.createNotStarted("routemind.messaging.publish", registry)
				.contextualName("publish routemind event")
				.lowCardinalityKeyValue("routemind.boundary", "messaging")
				.lowCardinalityKeyValue("messaging.system", "rabbitmq")
				.lowCardinalityKeyValue("messaging.operation.name", "publish");
		if (joinPoint.getArgs().length == 1 && joinPoint.getArgs()[0] instanceof EventEnvelope event) {
			String tenantKey = telemetry.tenantKey(event.tenantId());
			observation.lowCardinalityKeyValue("messaging.destination.name", event.eventType())
					.highCardinalityKeyValue("routemind.event_id", event.eventId().toString())
					.highCardinalityKeyValue("routemind.order_id", event.aggregateId().toString())
					.highCardinalityKeyValue("routemind.correlation_id", event.correlationId().toString())
					.highCardinalityKeyValue("routemind.trace_id", event.traceId())
					.highCardinalityKeyValue("routemind.tenant_key", tenantKey);
			telemetry.record("trace", "messaging", tenantKey);
			telemetry.record("metric", "messaging", tenantKey);
		}
		return proceed(joinPoint, observation);
	}

	@Around("execution(public * com.routemind.business.application.outbox.OutboxRelay.publishDue(..))")
	public Object observeWorker(ProceedingJoinPoint joinPoint) throws Throwable {
		Observation observation = Observation.createNotStarted("routemind.worker.outbox", registry)
				.contextualName("run outbox relay")
				.lowCardinalityKeyValue("routemind.boundary", "worker")
				.lowCardinalityKeyValue("routemind.worker.name", "outbox-relay");
		return proceed(joinPoint, observation);
	}

	@Around("execution(public * com.routemind.business.application.dispatch.DispatchDecisionLedgerService.record(..))")
	public Object observeDecision(ProceedingJoinPoint joinPoint) throws Throwable {
		Observation observation = Observation.createNotStarted("routemind.decision.record", registry)
				.contextualName("record dispatch decision")
				.lowCardinalityKeyValue("routemind.boundary", "decision")
				.lowCardinalityKeyValue("db.system.name", "postgresql");
		for (Object argument : joinPoint.getArgs()) {
			if (argument instanceof java.util.UUID orderId) {
				observation.highCardinalityKeyValue("routemind.order_id", orderId.toString());
			}
			else if (argument instanceof DispatchAssignmentCommand command) {
				observation.highCardinalityKeyValue("routemind.decision_id", command.requestId())
						.lowCardinalityKeyValue("routemind.strategy", command.strategy());
			}
		}
		return proceed(joinPoint, observation);
	}

	private static Object proceed(ProceedingJoinPoint joinPoint, Observation observation) throws Throwable {
		observation.start();
		try (Observation.Scope ignored = observation.openScope()) {
			return joinPoint.proceed();
		}
		catch (Throwable failure) {
			observation.error(failure);
			throw failure;
		}
		finally {
			observation.stop();
		}
	}
}
