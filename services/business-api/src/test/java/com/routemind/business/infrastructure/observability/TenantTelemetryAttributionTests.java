package com.routemind.business.infrastructure.observability;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.application.observability.TelemetryAttribution;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class TenantTelemetryAttributionTests {

	private static final String SECRET = "test-telemetry-attribution-key-32-characters";

	@Test
	void pseudonymizesAndBoundsTenantKeysWithoutRawIdentity() {
		SimpleMeterRegistry registry = new SimpleMeterRegistry();
		TenantTelemetryAttribution attribution = new TenantTelemetryAttribution(SECRET, 2, registry);
		UUID first = UUID.randomUUID();
		UUID second = UUID.randomUUID();

		String firstKey = attribution.tenantKey(first);
		assertThat(firstKey).matches("rtk_[0-9a-f]{24}").doesNotContain(first.toString());
		assertThat(attribution.tenantKey(first)).isEqualTo(firstKey);
		assertThat(attribution.tenantKey(second)).matches("rtk_[0-9a-f]{24}").isNotEqualTo(firstKey);
		assertThat(attribution.tenantKey(UUID.randomUUID())).isEqualTo(TelemetryAttribution.OVERFLOW_KEY);
		assertThat(attribution.activeKeyCount()).isEqualTo(2);

		attribution.record("trace", "http", firstKey);
		assertThat(registry.get("routemind.telemetry.attributed.records")
				.tags("service", "business-api", "signal", "trace", "operation", "http",
						"tenant_key", firstKey)
				.counter().count()).isEqualTo(1.0);
	}

	@Test
	void rejectsWeakSecretsAndUnboundedDimensions() {
		SimpleMeterRegistry registry = new SimpleMeterRegistry();
		assertThatThrownBy(() -> new TenantTelemetryAttribution("weak", 64, registry))
				.isInstanceOf(IllegalArgumentException.class).hasMessageContaining("32 characters");
		assertThatThrownBy(() -> new TenantTelemetryAttribution(SECRET, 257, registry))
				.isInstanceOf(IllegalArgumentException.class).hasMessageContaining("between 1 and 256");
		TenantTelemetryAttribution attribution = new TenantTelemetryAttribution(SECRET, 64, registry);
		assertThatThrownBy(() -> attribution.record("TRACE!", "http", "rtk_unattributed"))
				.isInstanceOf(IllegalArgumentException.class).hasMessageContaining("dimension");
	}
}
