package com.routemind.business.application.courier;

import java.util.Optional;

public interface CourierCommandIdempotencyRepository {

	CourierCommandIdempotency save(CourierCommandIdempotency record);

	Optional<CourierCommandIdempotency> findByKey(String key);
}
