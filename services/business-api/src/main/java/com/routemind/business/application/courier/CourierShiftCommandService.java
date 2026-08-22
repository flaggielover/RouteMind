package com.routemind.business.application.courier;

import com.routemind.business.domain.courier.CourierShift;
import com.routemind.business.domain.courier.CourierShiftStatus;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.outbox.OutboxMessage;
import com.routemind.business.application.outbox.OutboxRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CourierShiftCommandService {

	private final CourierShiftRepository shifts;
	private final CourierCommandIdempotencyRepository idempotency;
	private final OutboxRepository outbox;
	private final Clock clock;

	public CourierShiftCommandService(CourierShiftRepository shifts,
			CourierCommandIdempotencyRepository idempotency, OutboxRepository outbox, Clock clock) {
		this.shifts = shifts;
		this.idempotency = idempotency;
		this.outbox = outbox;
		this.clock = clock;
	}

	@Transactional
	public CourierCommandResult transition(UUID courierId, CourierShiftStatus target, String actor,
			long expectedVersion, UUID correlationId, String traceId, String idempotencyKey) {
		requireActor(actor);
		String key = requireKey(idempotencyKey);
		String requestHash = fingerprint("shift", courierId.toString(), target.name(), Long.toString(expectedVersion));
		CourierCommandResult replay = replayIfPresent(key, requestHash, "shift");
		if (replay != null) return replay;
		CourierShift current = shifts.findById(courierId).orElse(null);
		if (current == null) {
			current = shifts.save(CourierShift.offline(courierId, clock.instant()));
		}
		if (current.version() != expectedVersion) throw new CourierCommandConflictException("stale_version");
		CourierShift saved = shifts.save(current.transitionTo(target, expectedVersion, clock.instant()));
		publish(saved, correlationId, traceId);
		idempotency.save(new CourierCommandIdempotency(key, requestHash, "shift", courierId, saved.status().name(),
				saved.version(), clock.instant()));
		return new CourierCommandResult(courierId, saved.status().name(), saved.version(), false);
	}

	private CourierCommandResult replayIfPresent(String key, String requestHash, String operation) {
		CourierCommandIdempotency existing = idempotency.findByKey(key).orElse(null);
		if (existing == null) return null;
		if (!existing.requestHash().equals(requestHash) || !existing.operation().equals(operation)) {
			throw new CourierCommandConflictException("idempotency_key_reused");
		}
		return new CourierCommandResult(existing.courierId(), existing.status(), existing.version(), true);
	}

	private void publish(CourierShift shift, UUID correlationId, String traceId) {
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "courier.shift.changed", clock.instant(),
				"business-api", shift.courierId(), shift.version(), correlationId, null, traceId,
				Map.of("courierId", shift.courierId().toString(), "status", shift.status().name(),
						"version", Long.toString(shift.version())));
		outbox.save(OutboxMessage.pending(event));
	}

	private static void requireActor(String actor) {
		if (!"courier".equals(actor)) throw new CourierCommandAuthorizationException("actor_not_authorized");
	}

	private static String requireKey(String key) {
		if (key == null || key.isBlank() || key.length() > 128 || key.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException("idempotency key must be 1-128 safe characters");
		}
		return key.trim();
	}

	private static String fingerprint(String... fields) {
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-256");
			for (String field : fields) {
				byte[] bytes = field.getBytes(StandardCharsets.UTF_8);
				digest.update(Integer.toString(bytes.length).getBytes(StandardCharsets.US_ASCII));
				digest.update((byte) ':');
				digest.update(bytes);
			}
			return HexFormat.of().formatHex(digest.digest());
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}
}
