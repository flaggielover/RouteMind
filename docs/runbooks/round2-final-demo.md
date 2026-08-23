# RouteMind Round 2 Final Demo

This runbook is the reproducible local demo and evidence sequence for the
Round 2 closure gate. It proves the checked-in repository behavior on the
configured Windows development machine; it does not claim production
deployment, device-lab coverage, or full research completion.

## Preconditions

- PowerShell, Python, Java 17, Maven wrapper, Node/npm, Docker Desktop, and
  GitHub CLI are installed.
- The repository is `F:\Projects\RouteMind` and `F:\Projects\RouteMind-Data`
  remains an external data boundary.
- No production credentials are needed. Local service checks use the committed
  Compose placeholders and local fixtures.

## Fast closure sequence

Run from the repository root. Stop on the first non-zero exit code.

```powershell
./scripts/verify.ps1
python scripts/round2-adversarial-audit.py
./scripts/full-gate.ps1
Push-Location apps/web
npm run test:e2e
Pop-Location
```

Expected markers are `PASS: RouteMind fast repository gate`, the four
adversarial-audit PASS lines, `PASS: RouteMind full available gate`, and a
Playwright summary with no failed tests. The browser gate covers desktop and
mobile role navigation, map/queue interaction, strategy registry, simulation
error state, unavailable live data, stale realtime state, and axe scans.

## Service-backed evidence sequence

These checks start and stop local Compose dependencies themselves. Run them
when service-backed evidence is required; each script prints its own exact
assertions and preserves failure log tails.

```powershell
./scripts/golden-delivery.ps1
./scripts/failure-degradation-e2e.ps1
./scripts/performance-realtime-gate.ps1
```

The first script exercises the durable order lifecycle, dispatch assignment,
idempotent commands, and projection status. The second verifies timeout,
dependency outage, bounded candidate input, and explicit degraded responses.
The third records deterministic dispatch/Twin/SSE latency, throughput, cursor,
ordering, and payload-size measurements.

## Remote confirmation

After a coherent checkpoint is pushed, observe the real workflow rather than
assuming local success:

```powershell
git push origin main
gh run list --workflow CI --limit 5
gh run watch <run-id> --exit-status
gh run view <run-id> --log-failed
```

Only a completed run with all required jobs green is valid remote evidence.
Formatting-only failures must be fixed and re-run; they are not waived.

## Claim boundary

The demo intentionally labels unavailable, degraded, fixture, replay, and
unmeasured states. Strategy quality deltas are shown only by the What-if and
Strategy Comparison components after a recorded comparison run; the active
policy card does not invent a score from a live snapshot.
