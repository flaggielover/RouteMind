package com.routemind.business.application.courier;

import com.routemind.business.domain.courier.CourierShift;
import java.util.Optional;
import java.util.UUID;

public interface CourierShiftRepository {

	CourierShift save(CourierShift shift);

	Optional<CourierShift> findById(UUID courierId);
}
