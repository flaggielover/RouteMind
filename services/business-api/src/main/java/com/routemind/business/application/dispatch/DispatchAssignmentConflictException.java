package com.routemind.business.application.dispatch;

public final class DispatchAssignmentConflictException extends RuntimeException {

    public DispatchAssignmentConflictException(String reason) {
        super(reason);
    }
}
