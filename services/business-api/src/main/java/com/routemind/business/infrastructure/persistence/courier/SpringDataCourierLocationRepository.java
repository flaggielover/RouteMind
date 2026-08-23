package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.domain.courier.CourierLocation;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;
import jakarta.persistence.LockModeType;

interface SpringDataCourierLocationRepository extends JpaRepository<CourierLocationEntity, UUID> {
	@Lock(LockModeType.PESSIMISTIC_WRITE)
	@Query("select location from CourierLocationEntity location where location.courierId = :courierId")
	java.util.Optional<CourierLocationEntity> findByIdForUpdate(UUID courierId);
}

@Repository
class JpaCourierLocationStore implements CourierLocationStore {
	private final SpringDataCourierLocationRepository repository;
	private final SpringDataCourierLocationHistoryRepository history;

	JpaCourierLocationStore(SpringDataCourierLocationRepository repository,
			SpringDataCourierLocationHistoryRepository history) {
		this.repository = repository;
		this.history = history;
	}

	@Override
	@Transactional
	public CourierLocation save(CourierLocation location) {
		CourierLocationEntity existing = repository.findByIdForUpdate(location.courierId()).orElse(null);
		if (existing != null && existing.sequence() >= location.sequence()) return existing.toDomain();
		CourierLocationEntity entity = existing == null ? CourierLocationEntity.from(location) : existing;
		entity.apply(location);
		CourierLocation saved = repository.saveAndFlush(entity).toDomain();
		if (!history.existsByCourierIdAndSequence(location.courierId(), location.sequence())) {
			history.saveAndFlush(CourierLocationHistoryEntity.from(location));
			history.deleteByCourierIdAndSequenceLessThan(location.courierId(), Math.max(1, location.sequence() - 127));
		}
		return saved;
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
