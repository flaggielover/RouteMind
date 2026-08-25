package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.application.order.OrderCommandIdempotency;
import com.routemind.business.application.order.OrderCommandIdempotencyRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.infrastructure.persistence.TenantKey;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaOrderCommandIdempotencyRepository implements OrderCommandIdempotencyRepository {

	private final SpringDataOrderCommandIdempotencyRepository repository;
	private final TenantContext tenants;

	public JpaOrderCommandIdempotencyRepository(SpringDataOrderCommandIdempotencyRepository repository,
			TenantContext tenants) {
		this.repository = repository;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public OrderCommandIdempotency save(OrderCommandIdempotency record) {
		var tenantId = tenants.current().value();
		String physicalKey = TenantKey.encode(tenantId, record.key());
		OrderCommandIdempotencyEntity entity = repository.findByKeyAndTenantId(physicalKey, tenantId)
				.orElseGet(() -> OrderCommandIdempotencyEntity.from(record, tenantId));
		entity.apply(record);
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<OrderCommandIdempotency> findByKey(String key) {
		var tenantId = tenants.current().value();
		return repository.findByKeyAndTenantId(TenantKey.encode(tenantId, key), tenantId)
				.map(OrderCommandIdempotencyEntity::toDomain);
	}
}
