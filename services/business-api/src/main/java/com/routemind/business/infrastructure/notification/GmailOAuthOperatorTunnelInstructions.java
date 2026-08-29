package com.routemind.business.infrastructure.notification;

/** Sanitized manual SSH instructions; this class never starts or inspects SSH. */
final class GmailOAuthOperatorTunnelInstructions {

	private GmailOAuthOperatorTunnelInstructions() { }

	static String command(String knownHostsPath, int macPort, int windowsPort) {
		if (macPort < 1024 || macPort > 65535 || windowsPort < 1024 || windowsPort > 65535) {
			throw new IllegalArgumentException("loopback ports must be between 1024 and 65535");
		}
		String safeKnownHosts = knownHostsPath == null || knownHostsPath.isBlank()
				? "<EXTERNAL_KNOWN_HOSTS_PATH>" : knownHostsPath;
		return "ssh -N -T -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes "
				+ "-o CheckHostIP=yes -o UserKnownHostsFile=\"" + safeKnownHosts + "\" "
				+ "-R 127.0.0.1:" + macPort + ":127.0.0.1:" + windowsPort
				+ " suzhe@10.10.1.27";
	}
}
