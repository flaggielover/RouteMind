package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.AuthorizationCodeRequestUrl;
import com.google.api.client.auth.oauth2.TokenResponse;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.http.HttpTransport;
import com.google.api.client.util.store.FileDataStoreFactory;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.awt.Desktop;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/** Explicit operator command; never loaded by Spring or invoked by CI/startup. */
public final class GmailOAuthBootstrapCli {

	private static final Duration CALLBACK_TIMEOUT = Duration.ofMinutes(5);

	private GmailOAuthBootstrapCli() { }

	public static void main(String[] args) throws Exception {
		GmailOAuthBootstrapConfiguration configuration = GmailOAuthBootstrapConfiguration
				.fromEnvironment(System.getenv());
		Path repositoryRoot = Path.of(System.getenv().getOrDefault("ROUTEMIND_REPOSITORY_ROOT", "."));
		GmailOAuthPathPolicy.ValidatedPaths paths = GmailOAuthPathPolicy.validate(repositoryRoot, configuration);
		HttpTransport transport = GoogleNetHttpTransport.newTrustedTransport();
		FileDataStoreFactory store = new FileDataStoreFactory(paths.tokenStoreDirectory().toFile());
		GoogleAuthorizationCodeFlow flow = GoogleGmailOAuthBootstrap.buildFlow(
				transport, store, configuration, repositoryRoot);
		execute(flow, configuration.oauthUserId());
	}

	private static void execute(GoogleAuthorizationCodeFlow flow, String userId) throws Exception {
		CompletableFuture<Map<String, String>> callback = new CompletableFuture<>();
		HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
		server.createContext("/oauth2callback", exchange -> completeCallback(exchange, callback));
		server.start();
		String redirectUri = "http://127.0.0.1:" + server.getAddress().getPort() + "/oauth2callback";
		AuthorizationCodeRequestUrl authorization = GoogleGmailOAuthBootstrap.authorizationUrl(flow, redirectUri);
		String url = authorization.build();
		System.out.println("Open the displayed OAuth URL in the operator browser and approve only the requested scope.");
		System.out.println(url);
		try {
			openBrowser(url);
			Map<String, String> result = callback.get(CALLBACK_TIMEOUT.toMinutes(), TimeUnit.MINUTES);
			if (result.containsKey("error") || result.get("code") == null || result.get("code").isBlank()) {
				throw new IllegalStateException("OAuth authorization was not completed");
			}
			TokenResponse token = flow.newTokenRequest(result.get("code")).setRedirectUri(redirectUri).execute();
			flow.createAndStoreCredential(token, userId);
			System.out.println("OAuth bootstrap completed; credential material was stored outside the repository.");
			System.out.println("No Gmail message operation is performed by this command.");
		}
		finally {
			server.stop(0);
		}
	}

	private static void completeCallback(HttpExchange exchange, CompletableFuture<Map<String, String>> callback)
				throws IOException {
		Map<String, String> parameters = parseQuery(exchange.getRequestURI().getRawQuery());
		byte[] response = "OAuth callback received. You may close this tab.".getBytes(StandardCharsets.UTF_8);
		exchange.sendResponseHeaders(200, response.length);
		try (var output = exchange.getResponseBody()) {
			output.write(response);
		}
		callback.complete(parameters);
	}

	private static Map<String, String> parseQuery(String query) {
		Map<String, String> values = new HashMap<>();
		if (query == null || query.isBlank()) return values;
		for (String pair : query.split("&")) {
			String[] parts = pair.split("=", 2);
			String key = URLDecoder.decode(parts[0], StandardCharsets.UTF_8);
			String value = parts.length == 2 ? URLDecoder.decode(parts[1], StandardCharsets.UTF_8) : "";
			if (key.equals("code") || key.equals("error")) values.put(key, value);
		}
		return values;
	}

	private static void openBrowser(String url) {
		try {
			if (Desktop.isDesktopSupported()) Desktop.getDesktop().browse(URI.create(url));
		}
		catch (Exception ignored) {
			// The URL is already printed for an operator-controlled browser action.
		}
	}
}
