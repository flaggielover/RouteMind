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

## Material results

Implementation revision `1bae0447b562ed7fd4cf5c7fc8e10bc66713cd11`
passed all five jobs in GitHub Actions run `32701927556`. Campaign
`r3-315-20260824T073439Z-1bae0447b562` then executed every frozen instance in a
separate process. Full artifacts are under
`experiments/r3/R3-315/r3-315-20260824T073439Z-1bae0447b562` in
`ROUTEMIND_DATA_ROOT`; the committed compact ledger is
`docs/research/r3/results/exact-cross-check/solomon-prefix-eight-exact-results-v1.json`
with SHA-256
`61f9207c4b9788aaf320ded2953420347b419bb54370bc470e00aaeae6939c3f`.

- Selection/exclusion: 6 selected, 6 executed, 6 retained, 0 excluded.
- Enumeration: all six completed below the 109,600-sequence ceiling; feasible
  route-column counts ranged from 45 to 924. Constraint-monotone pruning explains
  why complete enumeration need not visit every possible ordered subset.
- Exact proof: all six returned CP-SAT `OPTIMAL`; every integer objective equaled
  its best bound and its fixed-cost-plus-distance recomputation.
- Verification: all six exact outputs and all six candidate outputs were complete
  and valid under the R3-314 independent verifier.
- Gap: candidate vehicle counts and transformed distances matched the exact path
  on all six, so every transformed same-vehicle distance gap is `0%`.
- Resource/identity: candidate elapsed times were about two seconds; exact solve
  times ranged from `0.004703` to `0.058999` seconds. Source, derived-instance,
  lineage, route-column, run-artifact, and summary digests were retained.
- Artifact integrity: all seven artifacts matched their sidecars; campaign
  summary SHA-256 is
  `8276a1e6c46a129ec6402148d2c3e909de3a8069c125fe818e401175f89ed05b`.

Final gates: `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`. The exact
ground-truth label applies only to each frozen eight-customer conservative
integer model. It does not prove source-double or 100-customer optimality and is
not an independent-software reproduction.
