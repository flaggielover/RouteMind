# RM-200 Architectural Hardening Audit Evidence

Date: 2026-08-23  
Starting commit: `6b742b7`  
Task graph transition: RM-200 `in_progress`; RM-201 through RM-209 pending.

## Commands and results

```text
git status --short --branch
## main...origin/main
?? .codex-tmp/

git rev-parse --short HEAD
6b742b7

python scripts/validate_control_plane.py
PASS: task graph schema, dependencies, states, and evidence rules

docker compose config --quiet
PASS (exit code 0)
```

The repository control plane and Compose configuration were valid before the
hardening task graph was extended. The existing Round 2 closure run
`32616211116` remains green at the starting checkpoint.

## Measured findings

- `apps/web/src/App.tsx`: 1,550 lines; `apps/web/src/styles.css`: 41,688 bytes.
- `services/compute-api/src/routemind_compute/api/app.py`: 947 lines.
- Largest algorithm modules are bounded and intentionally retained for focused
  follow-up: `vrptw.py` 391, `travel.py` 562, `rads.py` 492, and
  `twin_control.py` 391 lines.
- Java production classes remained below the audit threshold of 220 lines.
- Direct critical-path clock calls found in `CourierCommandController` fallback
  (`Instant.now()`), Python dispatch response generation (`datetime.now(UTC)`),
  and browser operational command IDs (`Date.now()`/`Math.random()`). Seeded
  simulation/demand/preparation generators were also identified and classified
  as deterministic-if-configured foundations.
- `DispatchAssignmentCommandService` persists an assignment audit keyed by
  idempotency, but no durable courier lease/generation/expiry or independent
  courier uniqueness check exists.
- `StrategyRegistry` validates decision shape/metadata, while VRPTW route
  feasibility is evaluated inside the planner; no independent solver verifier
  exists.

## Result

`docs/hardening/ROUND_2_CODEBASE_AUDIT.md` records severity, ownership-boundary
analysis, explicit limits, and the dependency-ordered response. No production
behavior or accepted capability was removed. RM-200 is eligible to pass after
this evidence and the final control-plane check; RM-201 and RM-202 are the next
hardening tasks.
