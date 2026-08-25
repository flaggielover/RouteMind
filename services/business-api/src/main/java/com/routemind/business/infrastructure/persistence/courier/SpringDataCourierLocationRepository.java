package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
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
	@Query("select location from CourierLocationEntity location where location.courierId = :courierId and location.tenantId = :tenantId")
	java.util.Optional<CourierLocationEntity> findByIdForUpdate(UUID courierId, UUID tenantId);

	java.util.Optional<CourierLocationEntity> findByCourierIdAndTenantId(UUID courierId, UUID tenantId);

	List<CourierLocationEntity> findAllByTenantId(UUID tenantId);
}

@Repository
class JpaCourierLocationStore implements CourierLocationStore {
	private final SpringDataCourierLocationRepository repository;
	private final SpringDataCourierLocationHistoryRepository history;
	private final TenantContext tenants;

	JpaCourierLocationStore(SpringDataCourierLocationRepository repository,
			SpringDataCourierLocationHistoryRepository history, TenantContext tenants) {
		this.repository = repository;
		this.history = history;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public CourierLocation save(CourierLocation location) {
		var tenantId = tenants.current().value();
		CourierLocationEntity existing = repository.findByIdForUpdate(location.courierId(), tenantId).orElse(null);
		if (existing != null && existing.sequence() >= location.sequence()) return existing.toDomain();
		if (existing == null && repository.existsById(location.courierId())) throw new TenantIsolationException();
		CourierLocationEntity entity = existing == null ? CourierLocationEntity.from(location, tenantId) : existing;
		entity.apply(location);
		CourierLocation saved = repository.saveAndFlush(entity).toDomain();
		if (!history.existsByCourierIdAndSequenceAndTenantId(location.courierId(), location.sequence(), tenantId)) {
			history.saveAndFlush(CourierLocationHistoryEntity.from(location, tenantId));
			history.deleteByCourierIdAndSequenceLessThanAndTenantId(location.courierId(),
					Math.max(1, location.sequence() - 127), tenantId);
		}
		return saved;
	}

	@Override
	@Transactional(readOnly = true)
	public List<CourierLocation> findAll() {
		return repository.findAllByTenantId(tenants.current().value()).stream().map(CourierLocationEntity::toDomain).toList();
	}

	@Override
	@Transactional(readOnly = true)
	public CourierLocation findById(UUID courierId) {
		return repository.findByCourierIdAndTenantId(courierId, tenants.current().value())
				.map(CourierLocationEntity::toDomain).orElseThrow();
	}
}
