package com.routemind.business.application.notification;

@FunctionalInterface
public interface NotificationProvider {

	NotificationResult send(NotificationRequest request);
}
