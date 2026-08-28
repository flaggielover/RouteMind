package com.routemind.business.application.notification;

import java.util.Objects;

public final class NotificationDeliveryWorker {

	@FunctionalInterface
	public interface Sleeper { void sleep(int attempt); }

	private final NotificationProvider provider;
	private final NotificationDeliveryLedger ledger;
	private final NotificationConsentChecker consent;
	private final int maxAttempts;
	private final Sleeper sleeper;

	public NotificationDeliveryWorker(NotificationProvider provider, NotificationDeliveryLedger ledger,
			NotificationConsentChecker consent, int maxAttempts, Sleeper sleeper) {
		this.provider = Objects.requireNonNull(provider, "provider");
		this.ledger = Objects.requireNonNull(ledger, "ledger");
		this.consent = Objects.requireNonNull(consent, "consent");
		if (maxAttempts < 1 || maxAttempts > 5) throw new IllegalArgumentException("maxAttempts must be 1..5");
		this.maxAttempts = maxAttempts;
		this.sleeper = Objects.requireNonNull(sleeper, "sleeper");
	}

	public NotificationResult deliver(NotificationRequest request) {
		Objects.requireNonNull(request, "request");
		var existing = ledger.completed(request.idempotencyKey());
		if (existing.isPresent()) return existing.get();
		if (!ledger.begin(request.idempotencyKey())) {
			// Do not persist an in-flight duplicate: the original worker owns the
			// idempotency record and must be able to publish its terminal result.
			return NotificationResult.suppressed(request, "duplicate_in_flight");
		}

		for (int attempt = 1; attempt <= maxAttempts; attempt++) {
			NotificationRequest current = request.forAttempt(attempt);
			NotificationConsent decision = consent.check(current);
			if (decision.decision() == NotificationConsent.Decision.SUPPRESS) {
				NotificationResult suppressed = NotificationResult.suppressed(current, decision.reason());
				ledger.complete(request.idempotencyKey(), suppressed);
				return suppressed;
			}
			if (decision.decision() == NotificationConsent.Decision.DEFER) {
				if (attempt == maxAttempts) {
					NotificationResult deferred = NotificationResult.suppressed(current, "defer_exhausted:" + decision.reason());
					ledger.complete(request.idempotencyKey(), deferred);
					return deferred;
				}
				sleeper.sleep(attempt);
				continue;
			}

			NotificationResult result = provider.send(current);
			if (result.status() != NotificationStatus.RETRYABLE || attempt == maxAttempts) {
				NotificationResult terminal = result.status() == NotificationStatus.RETRYABLE
						? NotificationResult.deadLetter(current, result.provenance().provider(), result.provenance().region(), "retry_exhausted")
						: result;
				ledger.complete(request.idempotencyKey(), terminal);
				return terminal;
			}
			sleeper.sleep(attempt);
		}
		throw new IllegalStateException("notification worker exhausted without terminal result");
	}
}
