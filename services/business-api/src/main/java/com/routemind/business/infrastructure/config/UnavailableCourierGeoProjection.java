package com.routemind.business.infrastructure.config;

import com.routemind.business.application.courier.CourierGeoProjection;
import com.routemind.business.application.courier.CourierProjectionInspection;
import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.NearbyCourier;
import java.util.List;

final class UnavailableCourierGeoProjection implements CourierGeoProjection {
	@Override
	public void upsert(CourierLocation location) {
		throw new IllegalStateException("courier_projection_unavailable");
	}

	@Override
	public List<NearbyCourier> nearby(double latitude, double longitude, double radiusKilometers) {
		throw new IllegalStateException("courier_projection_unavailable");
	}

	@Override
	public void rebuild(List<CourierLocation> locations) {
		throw new IllegalStateException("courier_projection_unavailable");
	}

	@Override
	public CourierProjectionInspection inspect() {
		return CourierProjectionInspection.unavailable("courier_projection_disabled");
	}
}
