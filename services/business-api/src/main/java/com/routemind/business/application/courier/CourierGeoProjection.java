package com.routemind.business.application.courier;

import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.NearbyCourier;
import java.util.List;

public interface CourierGeoProjection {

	void upsert(CourierLocation location);

	List<NearbyCourier> nearby(double latitude, double longitude, double radiusKilometers);

	void rebuild(List<CourierLocation> locations);

	default CourierProjectionInspection inspect() {
		return CourierProjectionInspection.unavailable("projection_inspection_not_supported");
	}
}
