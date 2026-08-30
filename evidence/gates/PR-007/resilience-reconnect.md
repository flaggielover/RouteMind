# PR-007 Resilience and Recovery Product Closure

Status: `IMPLEMENTED / LOCAL_EXECUTABLE_EVIDENCE_PASS`

## Bounded Docker recovery

- `docker compose config --quiet`: PASS.
- Active context: `desktop-linux`; the initial server probe timed out.
- The supported `docker desktop restart` remained bounded in `Stopping Docker
  Desktop` and was cancelled. `wsl --terminate docker-desktop` stopped only the
  Docker WSL distribution. Stale Docker Desktop/backend processes were then
  stopped by exact PID and the installed Desktop executable was relaunched.
- `docker version --format '{{.Server.Version}}'`: PASS, `29.6.2` on three
  bounded probes after recovery.
- No Docker prune, factory reset, volume removal, Compose `down -v`, database
  deletion, image deletion, or durable-state reset occurred.

## Implemented recovery evidence

- `scripts/golden-delivery.ps1` now maps compute
  `travel_fallback_reason` metadata into Java's required `fallbackReason`
  assignment field and rejects fallback without inspectable provenance.
- `scripts/failure-degradation-e2e.ps1` supplies monotonic location sequences,
  then proves Redis `DEGRADED -> PROJECTED` recovery rather than replaying a
  duplicate sequence.
- The same harness stops Java, observes the API unavailable, restarts Java,
  finds the pre-restart order in the authoritative PostgreSQL-backed operations
  snapshot, resumes SSE after the last durable cursor, and observes exactly one
  `order.created` event for the post-restart command.
- `apps/web/e2e/web.spec.ts` holds the second authenticated SSE request open to
  model a backend interruption. Desktop and mobile both show `Stream
  reconnecting`, retain `Live ready`, request `after=1`, suppress the replayed
  cursor/event, recover at cursor `2`, and render exactly two unique events.

## Executable gates

- `pwsh -File scripts/golden-delivery.ps1 -TimeoutSeconds 240`: PASS; RM-170
  delivery completed through PostgreSQL, RabbitMQ, Redis GEO, dispatch audit,
  and published Outbox event. Explicit local travel fallback reason:
  `transport_error`.
- `pwsh -File scripts/failure-degradation-e2e.ps1 -TimeoutSeconds 300`: PASS;
  Redis loss/recovery, compute outage/recovery, RabbitMQ Outbox recovery,
  duplicate command/event suppression, Java restart/snapshot recovery, SSE
  cursor resume, offline/stale command handling, and bounded dispatch timeout.
- Web Prettier source/config globs: PASS. The package-wide wrapper could not
  traverse a pre-existing ignored `playwright-report/data` directory with an
  abnormal local Windows ACL; no source formatting failure was reported.
- Web lint and typecheck: PASS.
- Web unit: PASS, 40 files / 112 tests.
- Web production build: PASS. The existing large-chunk advisory remains
  non-blocking.
- Full Playwright with line reporter: PASS, 36 passed / 2 device-conditional
  skipped across desktop and mobile, including Axe, stale/unavailable states,
  focus containment, overflow, and the new reconnect/deduplication case.

## Claim boundary

This is bounded local product recovery evidence. It is not production,
availability, disaster-recovery, RPO/RTO, provider, or performance validation.
Round 4 progress and frozen scientific claims are unchanged. External
operations: none; external cost: USD 0.00.
