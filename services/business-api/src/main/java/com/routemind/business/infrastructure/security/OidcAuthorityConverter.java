package com.routemind.business.infrastructure.security;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Set;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;

public final class OidcAuthorityConverter implements Converter<Jwt, Collection<GrantedAuthority>> {

	private final String rolesClaim;

	public OidcAuthorityConverter(String rolesClaim) {
		this.rolesClaim = rolesClaim;
	}

	@Override
	public Collection<GrantedAuthority> convert(Jwt source) {
		Set<GrantedAuthority> authorities = new LinkedHashSet<>();
		claimValues(source.getClaims().get("scope")).forEach(scope ->
			authorities.add(new SimpleGrantedAuthority("SCOPE_" + scope)));
		claimValues(source.getClaims().get(rolesClaim)).forEach(role ->
			authorities.add(new SimpleGrantedAuthority("ROLE_" + role.toUpperCase(java.util.Locale.ROOT))));
		return Set.copyOf(authorities);
	}

	static Set<String> claimValues(Object claim) {
		if (claim instanceof String value) {
			return Set.copyOf(java.util.Arrays.stream(value.split(" "))
					.map(String::trim).filter(item -> !item.isEmpty()).toList());
		}
		if (claim instanceof Collection<?> values) {
			return Set.copyOf(values.stream().filter(String.class::isInstance).map(String.class::cast)
					.map(String::trim).filter(item -> !item.isEmpty()).toList());
		}
		return Set.of();
	}
}
