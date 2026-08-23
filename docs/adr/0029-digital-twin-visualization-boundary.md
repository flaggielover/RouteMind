# ADR-0029: Digital Twin Visualization Boundary

Date: 2026-08-24  
Status: Accepted

## Context

Simulation controls and verified replay playback already expose separate
contracts. Operators still need one bounded view of clock progress, event
history, digest provenance, and the distinction between simulation, replay, and
RouteBench benchmark artifacts.

## Decision

Web owns a pure `projectTwinVisualization` projection and a read-oriented Twin
Visualization Center. It displays the selected source metadata, seed, scenario,
clock domain, speed, digest prefix, bounded latest-event timeline, and state
progress bars. Simulation and replay remain separate execution modes; benchmark
state is explicitly unavailable unless a benchmark artifact is attached. The
panel never creates simulation state, mutates replay artifacts, or claims
benchmark results from a simulation snapshot.

## Consequences

- Operators can scan a single state/provenance view without conflating clocks or
  evidence modes.
- Event streams remain bounded in the browser and preserve existing controls.
- Future benchmark integration must provide its own manifest and evidence
  contract before changing the unavailable state.
