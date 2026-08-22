package com.routemind.business.application.order;

import java.util.Optional;

public interface OrderCommandIdempotencyRepository {

	OrderCommandIdempotency save(OrderCommandIdempotency record);

	Optional<OrderCommandIdempotency> findByKey(String key);
}
