package com.routemind.business.infrastructure.projection.redis;

import com.routemind.business.application.courier.CourierGeoProjection;
import com.routemind.business.application.courier.CourierProjectionInspection;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.NearbyCourier;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.data.geo.Distance;
import org.springframework.data.geo.GeoResult;
import org.springframework.data.geo.GeoResults;
import org.springframework.data.geo.Metrics;
import org.springframework.data.geo.Point;
import org.springframework.data.redis.connection.RedisGeoCommands;
import org.springframework.data.redis.domain.geo.GeoReference;
import org.springframework.data.redis.core.StringRedisTemplate;

public class RedisCourierGeoProjection implements CourierGeoProjection {

	private final StringRedisTemplate redis;
	private final TenantContext tenants;

	public RedisCourierGeoProjection(StringRedisTemplate redis, TenantContext tenants) {
		this.redis = redis;
		this.tenants = tenants;
	}

	@Override
	public void upsert(CourierLocation location) {
		redis.opsForGeo().add(key(), new Point(location.point().longitude(), location.point().latitude()),
				location.courierId().toString());
	}

	@Override
	public List<NearbyCourier> nearby(double latitude, double longitude, double radiusKilometers) {
		if (radiusKilometers <= 0) {
			throw new IllegalArgumentException("radiusKilometers must be positive");
		}
		GeoResults<RedisGeoCommands.GeoLocation<String>> results = redis.opsForGeo().search(key(),
				GeoReference.fromCoordinate(new Point(longitude, latitude)),
				new Distance(radiusKilometers, Metrics.KILOMETERS));
		return results.getContent().stream().map(this::toNearby)
				.sorted(java.util.Comparator.comparingDouble(NearbyCourier::distanceKilometers)).toList();
	}

	@Override
	public void rebuild(List<CourierLocation> locations) {
		redis.delete(key());
		locations.forEach(this::upsert);
	}

	@Override
	public CourierProjectionInspection inspect() {
		try {
			String projectionKey = key();
			Set<String> members = redis.opsForZSet().range(projectionKey, 0, -1);
			Set<UUID> courierIds = members == null ? Set.of()
					: members.stream().map(UUID::fromString).collect(java.util.stream.Collectors.toUnmodifiableSet());
			return new CourierProjectionInspection(CourierProjectionInspection.Status.AVAILABLE, courierIds,
					Map.of("projection_key", projectionKey, "member_count", Integer.toString(courierIds.size())));
		}
		catch (RuntimeException failure) {
			return CourierProjectionInspection.unavailable("redis_projection_read_failed");
		}
	}

	private String key() {
		return "routemind:tenant:" + tenants.current().value() + ":couriers:geo";
	}

	private NearbyCourier toNearby(GeoResult<RedisGeoCommands.GeoLocation<String>> result) {
		return new NearbyCourier(UUID.fromString(result.getContent().getName()),
				result.getDistance() == null ? 0 : result.getDistance().getValue());
	}
}
