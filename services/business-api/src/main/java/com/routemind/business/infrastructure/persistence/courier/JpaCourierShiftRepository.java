package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierShiftRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.domain.courier.CourierShift;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaCourierShiftRepository implements CourierShiftRepository {

	private final SpringDataCourierShiftRepository repository;
	private final TenantContext tenants;

	public JpaCourierShiftRepository(SpringDataCourierShiftRepository repository, TenantContext tenants) {
		this.repository = repository;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public CourierShift save(CourierShift shift) {
		var tenantId = tenants.current().value();
		CourierShiftEntity entity = repository.findByCourierIdAndTenantId(shift.courierId(), tenantId).orElse(null);
		if (entity == null) {
			if (repository.existsById(shift.courierId())) throw new TenantIsolationException();
			entity = CourierShiftEntity.from(shift, tenantId);
		}
		else entity.apply(shift);
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<CourierShift> findById(UUID courierId) {
		return repository.findByCourierIdAndTenantId(courierId, tenants.current().value())
				.map(CourierShiftEntity::toDomain);
	}
}
