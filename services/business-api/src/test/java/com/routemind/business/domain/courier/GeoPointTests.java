package com.routemind.business.domain.courier;

import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import org.junit.jupiter.api.Test;

class GeoPointTests {

	@Test
	void rejectsCoordinatesOutsideEarthBounds() {
		assertThatIllegalArgumentException().isThrownBy(() -> new GeoPoint(91, 0));
		assertThatIllegalArgumentException().isThrownBy(() -> new GeoPoint(0, 181));
	}
}
