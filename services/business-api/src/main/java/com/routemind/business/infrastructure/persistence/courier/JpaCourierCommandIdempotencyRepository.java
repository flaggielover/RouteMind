package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierCommandIdempotency;
import com.routemind.business.application.courier.CourierCommandIdempotencyRepository;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaCourierCommandIdempotencyRepository implements CourierCommandIdempotencyRepository {

	private final SpringDataCourierCommandIdempotencyRepository repository;

	public JpaCourierCommandIdempotencyRepository(SpringDataCourierCommandIdempotencyRepository repository) {
		this.repository = repository;
	}

	@Override
	@Transactional
	public CourierCommandIdempotency save(CourierCommandIdempotency record) {
		return repository.saveAndFlush(CourierCommandIdempotencyEntity.from(record)).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<CourierCommandIdempotency> findByKey(String key) {
		return repository.findById(key).map(CourierCommandIdempotencyEntity::toDomain);
	}
}
