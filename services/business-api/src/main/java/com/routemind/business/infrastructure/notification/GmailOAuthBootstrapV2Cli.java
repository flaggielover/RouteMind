package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.TokenResponse;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.http.HttpTransport;
import com.google.api.client.util.store.FileDataStoreFactory;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/** Explicit V2 operator command; never loaded by Spring, CI, or startup. */
public final class GmailOAuthBootstrapV2Cli {

	static final Duration BOOTSTRAP_TIMEOUT = Duration.ofMinutes(15);

	private GmailOAuthBootstrapV2Cli() { }

	public static void main(String[] args) throws Exception {
		if (args.length != 0) {
			throw new IllegalArgumentException("Gmail OAuth bootstrap V2 accepts no arguments");
		}
		GmailOAuthBootstrapV2Configuration configuration = GmailOAuthBootstrapV2Configuration
				.fromEnvironment(System.getenv());
		Path repositoryRoot = Path.of(System.getenv().getOrDefault("ROUTEMIND_REPOSITORY_ROOT", "."));
		Path knownHosts = GmailOAuthOperatorTunnelPolicy.validateKnownHosts(
				repositoryRoot, configuration.knownHostsFile());
		execute(configuration, knownHosts, repositoryRoot);
	}

	static void execute(GmailOAuthBootstrapV2Configuration configuration,
			Path knownHosts, Path repositoryRoot) throws Exception {
		GmailOAuthBootstrapV2Session session = new GmailOAuthBootstrapV2Session();
		CompletableFuture<Boolean> preflight = new CompletableFuture<>();
		CompletableFuture<GmailOAuthBootstrapV2Session.Callback> callback = new CompletableFuture<>();
		HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
		server.createContext(GmailOAuthBootstrapV2Session.PREFLIGHT_PATH,
				exchange -> handlePreflight(exchange, session, preflight));
		server.createContext(GmailOAuthBootstrapV2Session.CALLBACK_PATH,
				exchange -> handleCallback(exchange, session, callback));
		server.start();
		int windowsPort = server.getAddress().getPort();
		String redirectUri = "http://127.0.0.1:" + configuration.macLoopbackPort()
				+ GmailOAuthBootstrapV2Session.CALLBACK_PATH;
		long deadline = System.nanoTime() + BOOTSTRAP_TIMEOUT.toNanos();
		try {
			System.out.println("Windows OAuth listener is bound only to 127.0.0.1:" + windowsPort + ".");
			System.out.println("Run this SSH command manually in a separate Windows terminal;"
					+ " type the Mac password there:");
			System.out.println(GmailOAuthOperatorTunnelInstructions.command(
					knownHosts.toString(), configuration.macLoopbackPort(), windowsPort));
			System.out.println("After the tunnel is running, open this Mac URL to prove callback reachability:");
			System.out.println("http://127.0.0.1:" + configuration.macLoopbackPort()
					+ GmailOAuthBootstrapV2Session.PREFLIGHT_PATH);

			await(preflight, deadline, "OAuth tunnel preflight did not complete");
			if (!session.preflightPassed()) {
				throw new IllegalStateException("OAuth tunnel preflight did not pass");
			}
			HttpTransport transport = GoogleNetHttpTransport.newTrustedTransport();
			FileDataStoreFactory store = new FileDataStoreFactory(
					GmailOAuthPathPolicy.validate(repositoryRoot, configuration.oauth())
							.tokenStoreDirectory().toFile());
			GoogleAuthorizationCodeFlow flow = GoogleGmailOAuthBootstrap.buildFlow(
					transport, store, configuration.oauth(), repositoryRoot);
			String authorizationUrl = session.authorizationUrl(flow, redirectUri).build();
			System.out.println("Tunnel preflight passed. Open this OAuth URL manually on the Mac:");
			System.out.println(authorizationUrl);

			GmailOAuthBootstrapV2Session.Callback result = await(
					callback, deadline, "OAuth callback did not complete");
			if (!result.accepted()) {
				throw new IllegalStateException("OAuth callback was rejected");
			}
			TokenResponse token = flow.newTokenRequest(result.code())
					.setRedirectUri(redirectUri).execute();
			flow.createAndStoreCredential(token, configuration.oauth().oauthUserId());
			System.out.println("OAuth bootstrap V2 completed; credentials remain in the external Windows store.");
			System.out.println("No Gmail message operation or email send is performed by this command.");
		}
		catch (TimeoutException exception) {
			session.fail("bootstrap timeout");
			throw exception;
		}
		finally {
			server.stop(0);
		}
	}

	private static <T> T await(CompletableFuture<T> future, long deadline, String message)
			throws Exception {
		long remaining = deadline - System.nanoTime();
		if (remaining <= 0) {
			throw new TimeoutException(message);
		}
		try {
			return future.get(remaining, TimeUnit.NANOSECONDS);
		}
		catch (TimeoutException exception) {
			throw new TimeoutException(message);
		}
	}

	private static void handlePreflight(HttpExchange exchange,
			GmailOAuthBootstrapV2Session session, CompletableFuture<Boolean> preflight) throws IOException {
		if (!GmailOAuthBootstrapV2Session.PREFLIGHT_PATH.equals(exchange.getRequestURI().getPath())
				|| !"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
			write(exchange, 404, "preflight rejected");
			return;
		}
		try {
			session.recordPreflight();
			preflight.complete(true);
			write(exchange, 200, GmailOAuthBootstrapV2Session.PREFLIGHT_RESPONSE);
		}
		catch (IllegalStateException exception) {
			session.fail("duplicate OAuth tunnel preflight");
			preflight.completeExceptionally(exception);
			write(exchange, 409, "preflight rejected");
		}
	}

	private static void handleCallback(HttpExchange exchange,
			GmailOAuthBootstrapV2Session session,
			CompletableFuture<GmailOAuthBootstrapV2Session.Callback> callback) throws IOException {
		if (!GmailOAuthBootstrapV2Session.CALLBACK_PATH.equals(exchange.getRequestURI().getPath())
				|| !"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
			write(exchange, 404, "callback rejected");
			return;
		}
		try {
			GmailOAuthBootstrapV2Session.Callback result = session.callback(exchange.getRequestURI());
			callback.complete(result);
			write(exchange, result.accepted() ? 200 : 400,
					result.accepted() ? "OAuth callback received. You may close this tab." : "callback rejected");
		}
		catch (IllegalArgumentException exception) {
			session.fail("malformed OAuth callback");
			callback.completeExceptionally(exception);
			write(exchange, 400, "callback rejected");
		}
	}

	private static void write(HttpExchange exchange, int status, String body) throws IOException {
		byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
		exchange.sendResponseHeaders(status, bytes.length);
		try (var output = exchange.getResponseBody()) {
			output.write(bytes);
		}
	}
}
