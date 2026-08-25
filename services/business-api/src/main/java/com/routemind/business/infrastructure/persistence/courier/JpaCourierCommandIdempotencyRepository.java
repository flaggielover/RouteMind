package com.routemind.business.infrastructure.persistence.courier;

import com.routemind.business.application.courier.CourierCommandIdempotency;
import com.routemind.business.application.courier.CourierCommandIdempotencyRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.infrastructure.persistence.TenantKey;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaCourierCommandIdempotencyRepository implements CourierCommandIdempotencyRepository {

	private final SpringDataCourierCommandIdempotencyRepository repository;
	private final TenantContext tenants;

	public JpaCourierCommandIdempotencyRepository(SpringDataCourierCommandIdempotencyRepository repository,
			TenantContext tenants) {
		this.repository = repository;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public CourierCommandIdempotency save(CourierCommandIdempotency record) {
		var tenantId = tenants.current().value();
		String physicalKey = TenantKey.encode(tenantId, record.key());
		CourierCommandIdempotencyEntity entity = repository.findByKeyAndTenantId(physicalKey, tenantId)
				.orElseGet(() -> CourierCommandIdempotencyEntity.from(record, tenantId));
		entity.apply(record);
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<CourierCommandIdempotency> findByKey(String key) {
		var tenantId = tenants.current().value();
		return repository.findByKeyAndTenantId(TenantKey.encode(tenantId, key), tenantId)
				.map(CourierCommandIdempotencyEntity::toDomain);
	}
}
