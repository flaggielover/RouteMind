package com.routemind.business.application.courier;

import com.routemind.business.domain.courier.CourierLocation;
import java.util.List;
import java.util.UUID;

public interface CourierLocationStore {

	CourierLocation save(CourierLocation location);

	List<CourierLocation> findAll();

	CourierLocation findById(UUID courierId);
}
