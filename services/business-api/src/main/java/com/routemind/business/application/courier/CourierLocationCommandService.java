package com.routemind.business.application.courier;

import com.routemind.business.application.outbox.OutboxRepository;
import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.event.EventEnvelope;
import com.routemind.business.domain.outbox.OutboxMessage;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CourierLocationCommandService {

	private final CourierLocationService locations;
	private final CourierCommandIdempotencyRepository idempotency;
	private final OutboxRepository outbox;
	private final Clock clock;

	public CourierLocationCommandService(CourierLocationService locations,
			CourierCommandIdempotencyRepository idempotency, OutboxRepository outbox, Clock clock) {
		this.locations = locations;
		this.idempotency = idempotency;
		this.outbox = outbox;
		this.clock = clock;
	}

	@Transactional
	public CourierCommandResult record(UUID courierId, double latitude, double longitude, Instant observedAt,
			String actor, UUID correlationId, String traceId, String idempotencyKey) {
		if (!"courier".equals(actor)) throw new CourierCommandAuthorizationException("actor_not_authorized");
		String key = requireKey(idempotencyKey);
		String requestHash = fingerprint("location", courierId.toString(), Double.toString(latitude),
				Double.toString(longitude), observedAt.toString());
		CourierCommandResult replay = replayIfPresent(key, requestHash, "location");
		if (replay != null) return replay;
		CourierLocation location = new CourierLocation(courierId,
				new com.routemind.business.domain.courier.GeoPoint(latitude, longitude), observedAt);
		ProjectionWriteStatus projectionStatus = locations.record(location);
		String status = projectionStatus.name();
		publish(location, projectionStatus, correlationId, traceId);
		idempotency.save(new CourierCommandIdempotency(key, requestHash, "location", courierId, status, 0,
				clock.instant()));
		return new CourierCommandResult(courierId, status, 0, false);
	}

	private CourierCommandResult replayIfPresent(String key, String requestHash, String operation) {
		CourierCommandIdempotency existing = idempotency.findByKey(key).orElse(null);
		if (existing == null) return null;
		if (!existing.requestHash().equals(requestHash) || !existing.operation().equals(operation)) {
			throw new CourierCommandConflictException("idempotency_key_reused");
		}
		return new CourierCommandResult(existing.courierId(), existing.status(), existing.version(), true);
	}

	private void publish(CourierLocation location, ProjectionWriteStatus projectionStatus, UUID correlationId,
			String traceId) {
		EventEnvelope event = new EventEnvelope("1.0", UUID.randomUUID(), "courier.location.updated", clock.instant(),
				"business-api", location.courierId(), 1, correlationId, null, traceId,
				Map.of("courierId", location.courierId().toString(), "latitude", Double.toString(location.point().latitude()),
						"longitude", Double.toString(location.point().longitude()), "observedAt", location.observedAt().toString(),
						"projectionStatus", projectionStatus.name()));
		outbox.save(OutboxMessage.pending(event));
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
