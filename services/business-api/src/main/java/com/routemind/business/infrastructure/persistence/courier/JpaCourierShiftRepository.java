package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierShiftRepository;
import com.routemind.business.domain.courier.CourierShift;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaCourierShiftRepository implements CourierShiftRepository {

	private final SpringDataCourierShiftRepository repository;

	public JpaCourierShiftRepository(SpringDataCourierShiftRepository repository) {
		this.repository = repository;
	}

	@Override
	@Transactional
	public CourierShift save(CourierShift shift) {
		CourierShiftEntity entity = repository.findById(shift.courierId()).orElse(null);
		if (entity == null) entity = CourierShiftEntity.from(shift);
		else entity.apply(shift);
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<CourierShift> findById(UUID courierId) {
		return repository.findById(courierId).map(CourierShiftEntity::toDomain);
	}
}
