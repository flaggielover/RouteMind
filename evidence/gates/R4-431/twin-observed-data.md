# R4-431 Observed Twin Data Readiness and Blocker

Disposition: `BLOCKED / LOCAL_PREPARATION_CLOSED`

The repository already implements source/split contracts, immutable calibration
and held-out identities, calibration, held-out validation, drift, non-fidelity,
provenance, deletion-policy checks, and synthetic negative-path tests. External
storage is accessed only through `ROUTEMIND_DATA_ROOT`.

The current external data root contains public Solomon benchmarks and 640
simulated deterministic policy observations. It contains no owner-authorized
observed Twin calibration/held-out dataset with consent, privacy, retention,
quality, leakage, split, and deletion approvals. Synthetic data cannot satisfy
this task. Reactivate only when the owner supplies and approves such a dataset
without exposing it to Git.
