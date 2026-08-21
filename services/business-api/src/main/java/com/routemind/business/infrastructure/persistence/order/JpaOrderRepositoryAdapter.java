package com.routemind.business.infrastructure.persistence.order;

import com.routemind.business.application.order.OrderRepository;
import com.routemind.business.domain.order.Order;
import com.routemind.business.domain.order.OrderId;
import java.util.Optional;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JpaOrderRepositoryAdapter implements OrderRepository {

	private final SpringDataOrderRepository repository;

	public JpaOrderRepositoryAdapter(SpringDataOrderRepository repository) {
		this.repository = repository;
	}

	@Override
	@Transactional
	public Order save(Order order) {
		OrderEntity entity = repository.findById(order.id().value()).orElse(null);
		if (entity == null) {
			entity = OrderEntity.from(order);
		} else {
			entity.apply(order);
		}
		return repository.saveAndFlush(entity).toDomain();
	}

	@Override
	@Transactional(readOnly = true)
	public Optional<Order> findById(OrderId id) {
		return repository.findById(id.value()).map(OrderEntity::toDomain);
	}
}
