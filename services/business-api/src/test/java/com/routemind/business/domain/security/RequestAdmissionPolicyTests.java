package com.routemind.business.domain.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class RequestAdmissionPolicyTests {

	private static final RequestPolicy POLICY = new RequestPolicy("rate-v1", RequestPolicyScope.PRINCIPAL, 60, 10, 2,
			1024, 8, 80);

	private static RequestDescriptor request(boolean command) {
		return new RequestDescriptor("POST", "/orders", "principal-1", 100, 2, 20, true, false, command, true);
	}

	@Test
	void allowsWithinLimitsAndProducesStablePolicyDigest() {
		AdmissionDecision first = RequestAdmissionPolicy.evaluate(POLICY, request(true), new UsageSnapshot(11, 10));
		AdmissionDecision second = RequestAdmissionPolicy.evaluate(POLICY, request(true), new UsageSnapshot(11, 10));

		assertThat(first.outcome()).isEqualTo(AdmissionOutcome.ALLOW);
		assertThat(first.reason()).isEqualTo("admitted");
		assertThat(first.policyDigest()).isEqualTo(second.policyDigest());
	}

	@Test
	void throttlesAtBurstBoundaryWithDeterministicRetryAfter() {
		AdmissionDecision decision = RequestAdmissionPolicy.evaluate(POLICY, request(false), new UsageSnapshot(12, 17));

		assertThat(decision.outcome()).isEqualTo(AdmissionOutcome.THROTTLE);
		assertThat(decision.reason()).isEqualTo("rate_limit_exceeded");
		assertThat(decision.retryAfterSeconds()).isEqualTo(43);
	}

	@Test
	void rejectsMalformedAndOversizedInputBeforeRateLimitEvaluation() {
		RequestDescriptor malformed = new RequestDescriptor("POST", "/orders", "principal-1", 100, 2, 20, false,
				false, true, true);
		RequestDescriptor oversized = new RequestDescriptor("POST", "/orders", "principal-1", 2048, 2, 20, true,
				false, false, true);

		assertThat(RequestAdmissionPolicy.evaluate(POLICY, malformed, new UsageSnapshot(99, 1)).reason())
				.isEqualTo("invalid_utf8");
		assertThat(RequestAdmissionPolicy.evaluate(POLICY, oversized, new UsageSnapshot(99, 1)).reason())
				.isEqualTo("body_limit");
	}

	@Test
	void requiresIdempotencyForCommandsAndRejectsControlCharacters() {
		RequestDescriptor commandWithoutKey = new RequestDescriptor("POST", "/orders", "principal-1", 100, 2, 20,
				true, false, true, false);
		RequestDescriptor controls = new RequestDescriptor("POST", "/orders", "principal-1", 100, 2, 20, true, true,
				false, true);

		assertThat(RequestAdmissionPolicy.evaluate(POLICY, commandWithoutKey, new UsageSnapshot(0, 0)).reason())
				.isEqualTo("idempotency_key_required");
		assertThat(RequestAdmissionPolicy.evaluate(POLICY, controls, new UsageSnapshot(0, 0)).reason())
				.isEqualTo("control_character");
	}

	@Test
	void rejectsInvalidPolicyAndMeasurementsAtConstruction() {
		assertThatThrownBy(() -> new RequestPolicy("rate-v1", RequestPolicyScope.PRINCIPAL, 0, 10, 0, 10, 1, 1))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("limits");
		assertThatThrownBy(() -> new UsageSnapshot(-1, 0)).isInstanceOf(IllegalArgumentException.class);
	}
}
