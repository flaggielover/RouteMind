package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.domain.courier.CourierLocation;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

interface SpringDataCourierLocationRepository extends JpaRepository<CourierLocationEntity, UUID> {
}

@Repository
class JpaCourierLocationStore implements CourierLocationStore {
	private final SpringDataCourierLocationRepository repository;

	JpaCourierLocationStore(SpringDataCourierLocationRepository repository) {
		this.repository = repository;
	}

	@Override
	@Transactional
	public CourierLocation save(CourierLocation location) {
		CourierLocationEntity entity = repository.findById(location.courierId()).orElseGet(() ->
				CourierLocationEntity.from(location));
		entity.apply(location);
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public List<CourierLocation> findAll() {
		return repository.findAll().stream().map(CourierLocationEntity::toDomain).toList();
	}

	@Override
	@Transactional(readOnly = true)
	public CourierLocation findById(UUID courierId) {
		return repository.findById(courierId).map(CourierLocationEntity::toDomain).orElseThrow();
	}
}
