package com.routemind.business.application.security;

import com.routemind.business.domain.security.TenantId;
import java.util.Objects;
import org.springframework.stereotype.Component;

@Component
public final class TenantContext {

	private final ThreadLocal<TenantId> current = new ThreadLocal<>();

	public TenantId current() {
		TenantId tenant = current.get();
		return tenant == null ? TenantId.LEGACY : tenant;
	}

	public Scope open(TenantId tenant) {
		TenantId previous = current.get();
		current.set(Objects.requireNonNull(tenant, "tenant"));
		return new Scope(previous);
	}

	public final class Scope implements AutoCloseable {
		private final TenantId previous;
		private boolean closed;

		private Scope(TenantId previous) {
			this.previous = previous;
		}

		@Override
		public void close() {
			if (closed) {
				return;
			}
			closed = true;
			if (previous == null) {
				current.remove();
			}
			else {
				current.set(previous);
			}
		}
	}
}
