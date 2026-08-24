# R3-315 exact/reference cross-check evidence

## Preregistration checkpoint

- Manifest: `docs/research/r3/manifests/exact-cross-check/solomon-prefix-eight-exact-v1.json`.
- Manifest SHA-256:
  `18785fe80e9f4f05490e9c06cf89c12d3457bab539e4dee4518ab8dc05f43e55`.
- Frozen: `2026-08-24T07:08:05Z`, before implementation-specific material
  execution, against revision `7588757ad08b97630239ebe8441e3fab345d140f`.
- Selection: all six R3-311 structural representatives, each transformed by the
  non-cherry-picked rule that retains the depot and eight smallest customer IDs.
- Candidate bound: OR-Tools RoutingModel 9.15.6755, two seconds, one thread per
  instance.
- Exact bound: exhaustive feasible-route enumeration followed by single-thread
  OR-Tools CP-SAT set partitioning, 30 seconds per instance and at most 109,600
  examined ordered customer sequences per instance.
- Proof boundary: `TRANSFORMED_MODEL_GROUND_TRUTH` requires complete enumeration,
  CP-SAT `OPTIMAL`, and acceptance by the R3-314 independent verifier. The proof
  applies only to the derived conservative scale-1000 model.
- Statistical disposition: `S-NOT-APPLICABLE`; this is a bounded correctness and
  gap audit, not a population-level hypothesis test.
- Preregistration checkpoint `117b755` passed all five GitHub Actions jobs in run
  `32700423191`.

Material execution remains prohibited until the manifest is committed and the
implementation checkpoint passes its required validation. Current gates:
`E-IN-PROGRESS / X-IN-PROGRESS / S-NOT-APPLICABLE / C-DEFERRED`.

## Implementation checkpoint

- `exact_cross_check.py` validates the frozen protocol and source-protocol
  digest, derives the deterministic prefix instance, runs the bounded candidate,
  exhaustively enumerates feasible transformed route columns, solves exact set
  partitioning, verifies both paths independently, and writes immutable JSON
  artifacts with SHA-256 sidecars.
- The existing RoutingModel implementation now exposes a canonical-instance
  helper, preserving R3-311 behavior while allowing the derived-instance
  candidate to use the identical frozen modeling semantics.
- The exact path is configuration-independent from RoutingModel but uses CP-SAT
  from the same OR-Tools 9.15.6755 distribution. This is not claimed as an
  independent software reproduction.
- Nineteen directed tests cover protocol drift, deterministic derivation,
  complete enumeration, capacity/time/scaling rejection, proven optimality,
  retained infeasibility, ground-truth suppression, hierarchical comparison,
  immutable artifacts, source checksum enforcement, output boundaries, campaign
  retention, and both CLI commands.
- Full local validation passed Java `80/80`; Python `371/371` at `95.16%`
  coverage with ruff/mypy/contracts; Web `92/92` plus production build; and all
  repository control gates.

No frozen C101/C201/R101/R201/RC101/RC201 derived instance was executed during
implementation validation. Material execution remains gated on a committed,
remote-green implementation revision.
