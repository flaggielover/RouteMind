package com.routemind.business.application.operations;

import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.application.order.OrderRepository;
import com.routemind.business.application.party.PartyRepository;
import java.time.Clock;
import java.time.Instant;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OperationsSnapshotService {

	private final OrderRepository orders;
	private final PartyRepository parties;
	private final CourierLocationStore courierLocations;
	private final Clock clock;

	public OperationsSnapshotService(OrderRepository orders, PartyRepository parties,
			CourierLocationStore courierLocations, Clock clock) {
		this.orders = Objects.requireNonNull(orders, "orders");
		this.parties = Objects.requireNonNull(parties, "parties");
		this.courierLocations = Objects.requireNonNull(courierLocations, "courierLocations");
		this.clock = Objects.requireNonNull(clock, "clock");
	}

	@Transactional(readOnly = true)
	public OperationsSnapshot read() {
		return new OperationsSnapshot(Instant.now(clock),
				orders.findAll().stream()
						.map(order -> new OperationsSnapshot.OrderSummary(order.id().value(), order.status().name(),
								order.version(), order.createdAt(), order.updatedAt()))
						.toList(),
				parties.findAll().stream()
						.map(party -> new OperationsSnapshot.PartySummary(party.id().value(), party.identity().type().name(),
								party.identity().displayName(), party.status().name()))
						.toList(),
				courierLocations.findAll().stream()
						.map(location -> new OperationsSnapshot.CourierLocationSummary(location.courierId(),
								location.point().latitude(), location.point().longitude(), location.observedAt()))
						.toList());
	}
}
