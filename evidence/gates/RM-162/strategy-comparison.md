# RM-162 Strategy Comparison Visualizations

Date: 2026-08-23

## Implemented boundary

- The Strategy route now runs a bounded multi-variant comparison through the
  existing What-if/RouteBench compute boundary. The candidate strategy is
  compared with the recorded baseline using the same scenario and provenance.
- Actual recorded metrics are shown as stable horizontal projections:
  assignment rate, simulated duration, observed compute runtime, and
  scenario-risk index. The panel does not combine them into a fabricated score.
- Completion, overtime, distance, utilization, fairness, and cost appear in a
  metric inventory as `Unavailable from recorded run` until a producer supplies
  those fields. Manifest, replay, output, recorded-run, and comparison digests
  remain inspectable for each result.

## Evidence

- `npm run check` passes 14 Web test files and 49 tests, plus Prettier, ESLint,
  TypeScript, and production build. Component tests cover actual bar values,
  unavailable metric inventory, provenance, clear, and error states; the
  adapter test covers multi-variant request serialization.
- `./scripts/web.ps1 -Action e2e` passes 23 desktop/mobile browser tests with
  one existing desktop-only skip. The Strategy scenario test runs both the
  What-if comparison and the strategy visualization against a mocked compute
  response, checking actual metrics, unavailable labels, provenance, and
  responsive screenshots; role and axe coverage remain green.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 142 tests at 95.88%,
  Web 49 unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L4 strategy lab and L6 strategy visualization evidence is complete.
GitHub Actions run `32608343277` passed all five jobs, including Python compute
and Web browser smoke. RM-162 is fully validated.
