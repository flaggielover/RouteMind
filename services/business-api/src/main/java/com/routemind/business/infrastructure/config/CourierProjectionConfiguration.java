package com.routemind.business.infrastructure.config;

import com.routemind.business.application.courier.CourierGeoProjection;
import com.routemind.business.application.courier.CourierLocationService;
import com.routemind.business.application.courier.CourierLocationStore;
import com.routemind.business.application.security.TenantContext;
import com.routemind.business.infrastructure.projection.redis.RedisCourierGeoProjection;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;

@Configuration(proxyBeanMethods = false)
public class CourierProjectionConfiguration {

	@Bean
	@ConditionalOnProperty(name = "routemind.redis.projection.enabled", havingValue = "true")
	CourierGeoProjection courierGeoProjection(StringRedisTemplate redis, TenantContext tenants) {
		return new RedisCourierGeoProjection(redis, tenants);
	}

	@Bean
	@ConditionalOnMissingBean(CourierGeoProjection.class)
	CourierGeoProjection unavailableCourierGeoProjection() {
		return new UnavailableCourierGeoProjection();
	}

	@Bean
	CourierLocationService courierLocationService(CourierLocationStore store, CourierGeoProjection projection) {
		return new CourierLocationService(store, projection);
	}
}
