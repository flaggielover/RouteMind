package com.routemind.business.application.preference;

public final class PreferenceConflictException extends RuntimeException {

	public PreferenceConflictException(String code) {
		super(code);
	}
}
