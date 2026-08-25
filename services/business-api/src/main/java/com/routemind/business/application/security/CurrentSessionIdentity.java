package com.routemind.business.application.security;

import java.util.Optional;

public interface CurrentSessionIdentity {

	Optional<SessionIdentity> current();
}
