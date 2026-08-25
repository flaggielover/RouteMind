package com.routemind.business.infrastructure.security;

import jakarta.servlet.ReadListener;
import jakarta.servlet.ServletInputStream;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;

final class BoundedBodyHttpServletRequest extends HttpServletRequestWrapper {

	private final byte[] body;

	private BoundedBodyHttpServletRequest(HttpServletRequest request, byte[] body) {
		super(request);
		this.body = body;
	}

	static BoundedBodyHttpServletRequest capture(HttpServletRequest request, long maximumBytes) throws IOException {
		if (maximumBytes >= Integer.MAX_VALUE) {
			throw new IllegalArgumentException("maximumBytes must fit in a bounded in-memory request");
		}
		byte[] body = request.getInputStream().readNBytes(Math.toIntExact(maximumBytes + 1));
		if (body.length > maximumBytes) {
			throw new BodyLimitExceededException();
		}
		return new BoundedBodyHttpServletRequest(request, body);
	}

	@Override
	public int getContentLength() {
		return body.length;
	}

	@Override
	public long getContentLengthLong() {
		return body.length;
	}

	@Override
	public ServletInputStream getInputStream() {
		ByteArrayInputStream input = new ByteArrayInputStream(body);
		return new ServletInputStream() {
			@Override
			public int read() {
				return input.read();
			}

			@Override
			public int read(byte[] target, int offset, int length) {
				return input.read(target, offset, length);
			}

			@Override
			public boolean isFinished() {
				return input.available() == 0;
			}

			@Override
			public boolean isReady() {
				return true;
			}

			@Override
			public void setReadListener(ReadListener listener) {
				try {
					if (!isFinished()) {
						listener.onDataAvailable();
					}
					if (isFinished()) {
						listener.onAllDataRead();
					}
				}
				catch (IOException exception) {
					listener.onError(exception);
				}
			}
		};
	}

	@Override
	public BufferedReader getReader() {
		String encoding = getCharacterEncoding();
		Charset charset = encoding == null ? StandardCharsets.UTF_8 : Charset.forName(encoding);
		return new BufferedReader(new InputStreamReader(getInputStream(), charset));
	}

	static final class BodyLimitExceededException extends IOException {
		private static final long serialVersionUID = 1L;
	}
}
