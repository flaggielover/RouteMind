package com.routemind.business.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.routemind.business.application.security.TenantContext;
import com.routemind.business.domain.security.TenantId;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;

class EdgeSecurityFilterTests {

	private static final Instant NOW = Instant.parse("2026-08-25T14:00:00Z");
	private static final TenantId TENANT_A = TenantId.parse("10000000-0000-0000-0000-000000000001");
	private static final TenantId TENANT_B = TenantId.parse("20000000-0000-0000-0000-000000000002");

	@AfterEach
	void clearSecurityContext() {
		SecurityContextHolder.clearContext();
	}

	@Test
	void rateLimitKeysAreTenantRoleActorAndRouteAware() throws Exception {
		TenantContext tenants = new TenantContext();
		EdgeSecurityFilter filter = filter(tenants, policy(1, 2));
		authenticate("subject-1", "ROLE_CUSTOMER");

		try (TenantContext.Scope ignored = tenants.open(TENANT_A)) {
			assertThat(execute(filter, "/api/v1/orders/10000000-0000-0000-0000-000000000010").getStatus())
					.isEqualTo(200);
			assertThat(execute(filter, "/api/v1/orders/20000000-0000-0000-0000-000000000020").getStatus())
					.isEqualTo(429);
		}
		try (TenantContext.Scope ignored = tenants.open(TENANT_B)) {
			assertThat(execute(filter, "/api/v1/orders/30000000-0000-0000-0000-000000000030").getStatus())
					.isEqualTo(200);
		}

		authenticate("subject-1", "ROLE_OPERATOR");
		try (TenantContext.Scope ignored = tenants.open(TENANT_A)) {
			assertThat(execute(filter, "/api/v1/orders/40000000-0000-0000-0000-000000000040").getStatus())
					.isEqualTo(200);
			assertThat(execute(filter, "/api/v1/orders/50000000-0000-0000-0000-000000000050").getStatus())
					.isEqualTo(200);
			MockHttpServletResponse throttled = execute(filter,
					"/api/v1/orders/60000000-0000-0000-0000-000000000060");
			assertThat(throttled.getStatus()).isEqualTo(429);
			assertThat(throttled.getHeader("Retry-After")).isEqualTo("60");
			assertThat(throttled.getHeader("X-RateLimit-Mode")).isEqualTo("primary");
		}
	}

	@Test
	void structuralFirewallRejectsSmugglingAndEncodedTraversal() throws Exception {
		TenantContext tenants = new TenantContext();
		EdgeSecurityFilter filter = filter(tenants, policy(10, 10));
		try (TenantContext.Scope ignored = tenants.open(TENANT_A)) {
			MockHttpServletRequest smuggling = request("/api/v1/system");
			smuggling.addHeader("Transfer-Encoding", "chunked");
			smuggling.addHeader("Content-Length", "10");
			MockHttpServletResponse smugglingResponse = execute(filter, smuggling);
			assertThat(smugglingResponse.getStatus()).isEqualTo(400);
			assertThat(smugglingResponse.getHeader("X-Edge-Decision"))
					.isEqualTo("request_smuggling_boundary");

			MockHttpServletResponse traversal = execute(filter, "/api/v1/%2e%2e/system");
			assertThat(traversal.getStatus()).isEqualTo(400);
			assertThat(traversal.getHeader("X-Edge-Decision")).isEqualTo("unsafe_path");

			MockHttpServletRequest unboundedBody = new MockHttpServletRequest("POST", "/api/v1/orders") {
				@Override
				public int getContentLength() {
					return -1;
				}

				@Override
				public long getContentLengthLong() {
					return -1;
				}
			};
			unboundedBody.setRequestURI("/api/v1/orders");
			unboundedBody.setContentType("application/json");
			unboundedBody.setContent(new byte[4097]);
			MockHttpServletResponse unboundedResponse = execute(filter, unboundedBody);
			assertThat(unboundedResponse.getStatus()).isEqualTo(413);
			assertThat(unboundedResponse.getHeader("X-Edge-Decision")).isEqualTo("body_limit");
		}
	}

	@Test
	void failingPrimaryUsesBoundedFallbackAndDoubleFailureFailsClosed() {
		EdgeRateLimitStore failing = (key, now, window, capacity) -> {
			throw new IllegalStateException("fixture unavailable");
		};
		var fallback = new ResilientEdgeRateLimiter(failing, new InMemoryFixedWindowRateLimitStore(4));
		assertThat(fallback.consume("key", NOW, 60, 1).mode()).isEqualTo("fallback");
		assertThat(fallback.consume("key", NOW, 60, 1).allowed()).isFalse();

		var unavailable = new ResilientEdgeRateLimiter(failing, failing).consume("key", NOW, 60, 1);
		assertThat(unavailable.unavailable()).isTrue();
		assertThat(unavailable.allowed()).isFalse();
	}

	@Test
	void trackedKeyCapacityIsStrictAndExpiredWindowsAreReclaimed() {
		InMemoryFixedWindowRateLimitStore store = new InMemoryFixedWindowRateLimitStore(1);
		store.consume("tenant-a", NOW, 60, 10);
		assertThatThrownBy(() -> store.consume("tenant-b", NOW, 60, 10))
				.isInstanceOf(IllegalStateException.class)
				.hasMessageContaining("capacity");
		assertThat(store.consume("tenant-b", NOW.plusSeconds(60), 60, 10).used()).isEqualTo(1);
	}

	private static EdgeSecurityFilter filter(TenantContext tenants, EdgeSecurityProperties properties) {
		return new EdgeSecurityFilter(tenants, properties,
				new ResilientEdgeRateLimiter(new InMemoryFixedWindowRateLimitStore(32),
						new InMemoryFixedWindowRateLimitStore(32)),
				Clock.fixed(NOW, ZoneOffset.UTC));
	}

	private static EdgeSecurityProperties policy(long customer, long operator) {
		return new EdgeSecurityProperties(true, "edge-v1", 60, 0, 1, 1, customer, 1, 1, 1, operator,
				32, 32, 8192, 1024, 1024, 4096);
	}

	private static void authenticate(String subject, String role) {
		SecurityContextHolder.getContext().setAuthentication(
				UsernamePasswordAuthenticationToken.authenticated(subject, "redacted",
						List.of(new SimpleGrantedAuthority(role))));
	}

	private static MockHttpServletResponse execute(EdgeSecurityFilter filter, String uri) throws Exception {
		return execute(filter, request(uri));
	}

	private static MockHttpServletRequest request(String uri) {
		MockHttpServletRequest request = new MockHttpServletRequest("GET", uri);
		request.setRequestURI(uri);
		request.setRemoteAddr("127.0.0.1");
		return request;
	}

	private static MockHttpServletResponse execute(EdgeSecurityFilter filter, MockHttpServletRequest request)
			throws Exception {
		MockHttpServletResponse response = new MockHttpServletResponse();
		filter.doFilter(request, response, new MockFilterChain());
		return response;
	}
}
