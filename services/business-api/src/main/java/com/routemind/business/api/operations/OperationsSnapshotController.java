package com.routemind.business.api.operations;

import com.routemind.business.application.operations.OperationsSnapshot;
import com.routemind.business.application.operations.OperationsSnapshotService;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/operations")
@CrossOrigin(origins = { "http://localhost:4173", "http://127.0.0.1:4173" })
public final class OperationsSnapshotController {

	private final OperationsSnapshotService service;

	public OperationsSnapshotController(OperationsSnapshotService service) {
		this.service = service;
	}

	@GetMapping("/snapshot")
	public OperationsSnapshotResponse snapshot() {
		return OperationsSnapshotResponse.from(service.read());
	}

	public record OperationsSnapshotResponse(String source, Instant generatedAt, List<OrderResponse> orders,
			List<PartyResponse> parties, List<CourierLocationResponse> courierLocations) {

		static OperationsSnapshotResponse from(OperationsSnapshot snapshot) {
			return new OperationsSnapshotResponse("live", snapshot.generatedAt(),
				snapshot.orders().stream().map(order -> new OrderResponse(order.id(), order.status(), order.version(),
						order.createdAt(), order.updatedAt())).toList(),
				snapshot.parties().stream().map(party -> new PartyResponse(party.id(), party.type(), party.displayName(),
						party.status())).toList(),
				snapshot.courierLocations().stream().map(location -> new CourierLocationResponse(location.courierId(),
						location.latitude(), location.longitude(), location.observedAt())).toList());
		}
	}

	public record OrderResponse(UUID id, String status, long version, Instant createdAt, Instant updatedAt) {
	}

	public record PartyResponse(UUID id, String type, String displayName, String status) {
	}

	public record CourierLocationResponse(UUID courierId, double latitude, double longitude, Instant observedAt) {
	}
}
