package com.routemind.business.application.preference;

public final class PreferenceAccessDeniedException extends RuntimeException {

	public PreferenceAccessDeniedException() {
		super("preference_scope_forbidden");
	}
}
