# Stage 0 Autonomous Control Plane Design

## Context

Reconnaissance found `F:\Projects\RouteMind` empty and not under Git. The adjacent
`RouteMind-Data` directory defines an external large-data boundary but contains no
application source or prior control state. Stage 0 therefore initializes rather
than normalizes the code repository.

## Design

The root control files form the recovery API for future sessions. `AGENTS.md`
defines immutable operating constraints, the master specification and architecture
define capability and ownership boundaries, `TASK_GRAPH.yaml` holds executable
dependency state, and progress/handoff files provide compact current state.

The task graph uses JSON syntax, which is valid YAML 1.2, so the Python standard
library can validate it before project dependencies exist. Validation rejects
unknown dependencies, cycles, invalid states, missing acceptance/gates, unproven
passed tasks, and tasks whose state contradicts dependency completion.

PowerShell scripts match the current workstation and provide bootstrap, doctor,
fast verification, full-gate, and resume entry points. They must fail loudly on
repository-state contradictions and must never require chat history.

## Architecture decisions

The initial implementation uses a modular monorepo and two principal runtimes:
Java owns durable business and consistency-sensitive behavior; Python owns compute,
dispatch, simulation, research, and bounded intelligence. PostgreSQL, RabbitMQ,
and Redis provide durable state, messaging, and hot/GEO state respectively. Large
data remains under `ROUTEMIND_DATA_ROOT`.

## Error and recovery behavior

Validation emits actionable errors and nonzero status. Resume shows Git state,
current task, next eligible candidates, and the fast gate. Failed task work retains
evidence under `evidence/failures/` or the external data root when large. A future
session can reconstruct the next action from committed files and Git alone.

## Verification

Stage 0 passes when all required files exist, the task graph is internally
consistent and acyclic, scripts parse, the resume path succeeds, evidence is
recorded, and the checkpoint is committed. The next task is RM-001 local
infrastructure, proving the control plane immediately drives implementation.
