package com.routemind.business.application.courier;

import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.NearbyCourier;
import java.util.List;
import java.util.Objects;

public class CourierLocationService {

	private final CourierLocationStore store;
	private final CourierGeoProjection projection;

	public CourierLocationService(CourierLocationStore store, CourierGeoProjection projection) {
		this.store = Objects.requireNonNull(store, "store");
		this.projection = Objects.requireNonNull(projection, "projection");
	}

	public ProjectionWriteStatus record(CourierLocation location) {
		store.save(location);
		try {
			projection.upsert(location);
			return ProjectionWriteStatus.PROJECTED;
		} catch (RuntimeException ignored) {
			return ProjectionWriteStatus.DEGRADED;
		}
	}

	public List<NearbyCourier> nearby(double latitude, double longitude, double radiusKilometers) {
		return projection.nearby(latitude, longitude, radiusKilometers);
	}

	public void rebuild() {
		projection.rebuild(store.findAll());
	}
}
