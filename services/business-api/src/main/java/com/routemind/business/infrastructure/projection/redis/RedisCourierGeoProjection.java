package com.routemind.business.infrastructure.projection.redis;

import com.routemind.business.application.courier.CourierGeoProjection;
import com.routemind.business.domain.courier.CourierLocation;
import com.routemind.business.domain.courier.NearbyCourier;
import java.util.List;
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

	private static final String KEY = "routemind:couriers:geo";
	private final StringRedisTemplate redis;

	public RedisCourierGeoProjection(StringRedisTemplate redis) {
		this.redis = redis;
	}

	@Override
	public void upsert(CourierLocation location) {
		redis.opsForGeo().add(KEY, new Point(location.point().longitude(), location.point().latitude()),
				location.courierId().toString());
	}

	@Override
	public List<NearbyCourier> nearby(double latitude, double longitude, double radiusKilometers) {
		if (radiusKilometers <= 0) {
			throw new IllegalArgumentException("radiusKilometers must be positive");
		}
		GeoResults<RedisGeoCommands.GeoLocation<String>> results = redis.opsForGeo().search(KEY,
				GeoReference.fromCoordinate(new Point(longitude, latitude)),
				new Distance(radiusKilometers, Metrics.KILOMETERS));
		return results.getContent().stream().map(this::toNearby)
				.sorted(java.util.Comparator.comparingDouble(NearbyCourier::distanceKilometers)).toList();
	}

	@Override
	public void rebuild(List<CourierLocation> locations) {
		redis.delete(KEY);
		locations.forEach(this::upsert);
	}

	private NearbyCourier toNearby(GeoResult<RedisGeoCommands.GeoLocation<String>> result) {
		return new NearbyCourier(UUID.fromString(result.getContent().getName()),
				result.getDistance() == null ? 0 : result.getDistance().getValue());
	}
}
