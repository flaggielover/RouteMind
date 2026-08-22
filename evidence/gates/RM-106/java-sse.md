# RM-106 Java Business Event SSE Feed

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `21beadc`
- Boundary: bounded read-only Java SSE projection over durable Outbox event records

## Transport and cursor behavior

`GET /api/v1/events/stream` serves `text/event-stream` from the Java business API.
The adapter reads the newest Outbox records in event order, assigns a bounded
monotonic projection cursor, and preserves the immutable `EventEnvelope` identity
fields. Each SSE item sets `id` to the decimal cursor and names the business
event type. `Last-Event-ID` takes precedence over the `after` query parameter and
replay is exclusive (`entry.cursor > cursor`), so a reconnect cannot reapply the
last delivered item.

The service caps each read at 64 entries. Cursors outside the retained window
return HTTP 409 so the browser can refresh its authoritative snapshot. Malformed
or non-canonical cursors return HTTP 400. The emitter has a five-second timeout;
timeout, send failure, and error callbacks log `event_stream_subscriber_lost`
and complete the emitter, bounding slow or disconnected subscribers.

## Executable evidence

1. `./scripts/business-api.ps1 -Action test` -> PASS; 57 Java tests, including
   exclusive cursor, retention-stale, batch-bound, and HTTP cursor validation tests.
2. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, Web 9 unit tests and production build.
3. `git diff --check` -> PASS before checkpoint commit.
4. GitHub Actions run `32565242420` -> PASS; all five jobs passed, including
   the clean Java runtime gate.

## Evidence limits

This is a local bounded projection over the Java Outbox read path. It does not
replace RabbitMQ durability or claim a distributed cursor allocator, load,
multi-instance fan-out, or production resilience validation. Retention and
staleness become explicit when a future durable event-stream store is introduced.
