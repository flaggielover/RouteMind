package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.application.order.OrderRepository;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.application.security.TenantIsolationException;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaOrderRepositoryAdapter implements OrderRepository {

	private final SpringDataOrderRepository repository;
	private final TenantContext tenants;

	public JpaOrderRepositoryAdapter(SpringDataOrderRepository repository, TenantContext tenants) {
		this.repository = repository;
		this.tenants = tenants;
	}

	@Override
	@Transactional
	public Order save(Order order) {
		var tenantId = tenants.current().value();
		OrderEntity entity = repository.findByIdAndTenantId(order.id().value(), tenantId).orElse(null);
		if (entity == null) {
			if (repository.existsById(order.id().value())) throw new TenantIsolationException();
			entity = OrderEntity.from(order, tenantId);
		} else {
			entity.apply(order);
		}
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<Order> findById(OrderId id) {
		return repository.findByIdAndTenantId(id.value(), tenants.current().value()).map(OrderEntity::toDomain);
	}

	@Override
	@Transactional(readOnly = true)
	public List<Order> findAll() {
		return repository.findAllByTenantId(tenants.current().value()).stream().map(OrderEntity::toDomain).toList();
	}
}
