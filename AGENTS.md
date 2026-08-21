# RouteMind Autonomous Engineering Constitution

The repository is the source of truth. Chat history is never authoritative.

## Startup protocol

1. Run `git status`, inspect the branch, remotes, and recent history.
2. Read `AGENTS.md`.
3. Read `MASTER_SPEC.md`.
4. Read `MASTER_ARCHITECTURE.md`.
5. Read `ROADMAP.md`.
6. Read `TASK_GRAPH.yaml`.
7. Read `PROGRESS.md`.
8. Read `HANDOFF.md`.
9. Run `./scripts/resume.ps1` and inspect relevant CI/test evidence.
10. Select the highest-priority unblocked task whose dependencies passed.
11. Implement, validate, record evidence, commit a coherent checkpoint, and continue.

## Non-negotiable architecture

- Preserve the Java/Python split. Java owns durable business state, transactions,
  state machines, consistency-sensitive APIs, and event production. Python owns
  dispatch, optimization, simulation, RADS, RouteBench, analytics, experiments,
  and higher-level agent intelligence.
- RabbitMQ, transactional Outbox, consumer Inbox/deduplication, Redis GEO, a
  travel-provider abstraction, Digital Twin, strategy control, RouteBench, RADS,
  research lineage, and multi-end product surfaces are planned capabilities.
  Stage or interface incomplete capabilities; do not erase or trivialize them.
- LLM agents may analyze, explain, and orchestrate experiments. They never own
  hard real-time dispatch correctness.
- Prefer strong modular boundaries. Do not create a network service without a
  deployment, scaling, ownership, or failure-isolation reason.
- PostgreSQL is durable truth. Redis is hot state, indexing, caching, or justified
  coordination, never the sole durable business record.

## Execution policy

- Fix broken main/build and repository integrity before feature work.
- Update `TASK_GRAPH.yaml` on every task transition. `passed` requires executable
  evidence; code existence alone is not completion.
- Use risk-based gates from `QUALITY_GATES.md`. Diagnose failures autonomously,
  preserve useful logs, and record blockers before moving to another safe task.
- Never fake completion, delete legitimate tests, weaken assertions to get green,
  hardcode expected outputs, or claim live/production/performance/resilience
  validation without matching evidence.
- Keep secrets out of code, Git, logs, and documentation. Use environment
  variables and committed examples with non-production placeholders.
- Preserve unrelated work. Never force-push or use destructive reset against
  unknown changes. Prefer small coherent commits after validation.
- Record consequential architecture decisions in `docs/adr/`; avoid ceremony for
  local implementation details.
- Missing paid services or credentials are bypassable when an interface, local
  provider, emulator, or fixture can preserve progress.
- Before interruption, refresh `TASK_GRAPH.yaml`, `PROGRESS.md`, and `HANDOFF.md`.

## Task selection

Choose in order: broken main/build, repository integrity, unblocked prerequisites,
critical-path architecture, high-value infrastructure, features, research
extensions, then justified cleanup. Do not ask the owner to choose routine work.
