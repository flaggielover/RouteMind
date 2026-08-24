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

Material execution remains prohibited until the manifest is committed and the
implementation checkpoint passes its required validation. Current gates:
`E-IN-PROGRESS / X-IN-PROGRESS / S-NOT-APPLICABLE / C-DEFERRED`.
