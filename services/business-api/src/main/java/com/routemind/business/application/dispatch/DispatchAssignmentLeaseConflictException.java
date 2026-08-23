package com.routemind.business.application.dispatch;

public final class DispatchAssignmentLeaseConflictException extends RuntimeException {

    public DispatchAssignmentLeaseConflictException(String reason) {
        super(reason);
    }
}
