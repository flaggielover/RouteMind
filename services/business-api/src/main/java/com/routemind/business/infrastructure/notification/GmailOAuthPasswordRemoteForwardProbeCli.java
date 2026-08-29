package com.routemind.business.infrastructure.notification;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Explicit synthetic-only probe for the password-authenticated remote forward. */
public final class GmailOAuthPasswordRemoteForwardProbeCli {

	static final Duration PROBE_TIMEOUT = Duration.ofMinutes(5);
	static final String PROBE_PATH = "/synthetic-probe";
	static final String PROBE_RESPONSE = "ROUTEMIND_SYNTHETIC_PROBE_OK";

	private GmailOAuthPasswordRemoteForwardProbeCli() { }

	public static void main(String[] args) throws Exception {
		if (args.length != 0) {
			throw new IllegalArgumentException("synthetic probe accepts no arguments");
		}
		GmailOAuthPasswordRemoteForwardConfiguration configuration =
				GmailOAuthPasswordRemoteForwardConfiguration.fromEnvironment(System.getenv());
		Path repositoryRoot = Path.of(System.getenv().getOrDefault("ROUTEMIND_REPOSITORY_ROOT", "."));
		Path knownHosts = GmailOAuthPasswordRemoteForwardPolicy.validate(repositoryRoot, configuration);
		execute(configuration, knownHosts);
	}

	static void execute(GmailOAuthPasswordRemoteForwardConfiguration configuration,
			Path knownHosts) throws Exception {
		AtomicInteger requestCount = new AtomicInteger();
		CompletableFuture<Boolean> probeResult = new CompletableFuture<>();
		HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
		server.createContext(PROBE_PATH, exchange -> handleProbe(exchange, requestCount, probeResult));
		server.start();
		int windowsPort = server.getAddress().getPort();
		List<String> command = GmailOAuthPasswordRemoteForwardCommand.build(
				knownHosts, configuration.macLoopbackPort(), windowsPort);
		Process ssh = new ProcessBuilder(command)
				.redirectInput(ProcessBuilder.Redirect.INHERIT)
				.redirectOutput(ProcessBuilder.Redirect.DISCARD)
				.redirectError(ProcessBuilder.Redirect.INHERIT)
				.start();
		try {
			System.out.println("SSH will prompt for the Mac password in this Windows terminal; type it manually.");
			System.out.println("No password is read, captured, echoed, logged, or persisted by RouteMind.");
			System.out.println("Open http://127.0.0.1:" + configuration.macLoopbackPort()
					+ PROBE_PATH + " in a Mac browser to send one synthetic request.");
			long deadline = System.nanoTime() + PROBE_TIMEOUT.toNanos();
			Boolean success = null;
			while (success == null && System.nanoTime() < deadline) {
				if (!ssh.isAlive()) {
					throw new IllegalStateException("SSH remote forward exited before synthetic probe");
				}
				success = probeResult.getNow(null);
				if (success == null) {
					Thread.sleep(100L);
				}
			}
			if (!Boolean.TRUE.equals(success) || requestCount.get() != 1) {
				throw new IllegalStateException("synthetic remote-forward probe did not complete exactly once");
			}
			if (!ssh.isAlive()) {
				throw new IllegalStateException("SSH remote forward exited during synthetic probe");
			}
			System.out.println("Synthetic loopback probe completed exactly once; OAuth was not started.");
		}
		finally {
			server.stop(0);
			ssh.destroy();
			if (ssh.isAlive()) {
				ssh.destroyForcibly();
			}
			ssh.waitFor(2, TimeUnit.SECONDS);
		}
	}

	private static void handleProbe(HttpExchange exchange, AtomicInteger requestCount,
			CompletableFuture<Boolean> probeResult) throws IOException {
		int count = requestCount.incrementAndGet();
		boolean valid = count == 1 && "GET".equalsIgnoreCase(exchange.getRequestMethod());
		byte[] response = (valid ? PROBE_RESPONSE : "synthetic probe rejected")
				.getBytes(StandardCharsets.UTF_8);
		exchange.sendResponseHeaders(valid ? 200 : 400, response.length);
		try (var output = exchange.getResponseBody()) {
			output.write(response);
		}
		if (valid) {
			probeResult.complete(true);
		}
		else {
			probeResult.completeExceptionally(new IllegalStateException("unexpected synthetic probe request"));
		}
	}
}
