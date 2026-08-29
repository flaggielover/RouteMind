package com.routemind.business.infrastructure.notification;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Deterministic, loopback-only OpenSSH command construction. */
final class GmailOAuthRemoteForwardCommand {

	private GmailOAuthRemoteForwardCommand() { }

	static List<String> build(Path identityFile, Path knownHostsFile, int macPort, int windowsPort) {
		if (windowsPort < 1024 || windowsPort > 65535) {
			throw new IllegalArgumentException("windowsPort must be between 1024 and 65535");
		}
		if (macPort < 1024 || macPort > 65535) {
			throw new IllegalArgumentException("macPort must be between 1024 and 65535");
		}
		List<String> command = new ArrayList<>();
		command.add("ssh.exe");
		command.add("-N");
		command.add("-T");
		command.add("-o");
		command.add("BatchMode=yes");
		command.add("-o");
		command.add("ExitOnForwardFailure=yes");
		command.add("-o");
		command.add("StrictHostKeyChecking=yes");
		command.add("-o");
		command.add("CheckHostIP=yes");
		command.add("-o");
		command.add("IdentitiesOnly=yes");
		command.add("-o");
		command.add("LogLevel=ERROR");
		command.add("-o");
		command.add("UserKnownHostsFile=" + knownHostsFile);
		command.add("-o");
		command.add("IdentityFile=" + identityFile);
		command.add("-o");
		command.add("PermitRemoteOpen=127.0.0.1:" + windowsPort);
		command.add("-R");
		command.add("127.0.0.1:" + macPort + ":127.0.0.1:" + windowsPort);
		command.add(GmailOAuthRemoteForwardConfiguration.MAC_USER + "@"
				+ GmailOAuthRemoteForwardConfiguration.MAC_HOST);
		return List.copyOf(command);
	}
}
