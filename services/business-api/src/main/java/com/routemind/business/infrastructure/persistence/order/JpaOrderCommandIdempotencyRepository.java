package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.application.order.OrderCommandIdempotency;
import com.routemind.business.application.order.OrderCommandIdempotencyRepository;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaOrderCommandIdempotencyRepository implements OrderCommandIdempotencyRepository {

	private final SpringDataOrderCommandIdempotencyRepository repository;

	public JpaOrderCommandIdempotencyRepository(SpringDataOrderCommandIdempotencyRepository repository) {
		this.repository = repository;
	}

	@Override
	@Transactional
	public OrderCommandIdempotency save(OrderCommandIdempotency record) {
		OrderCommandIdempotencyEntity entity = repository.findById(record.key())
				.orElseGet(() -> OrderCommandIdempotencyEntity.from(record));
		entity.apply(record);
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<OrderCommandIdempotency> findByKey(String key) {
		return repository.findById(key).map(OrderCommandIdempotencyEntity::toDomain);
	}
}
