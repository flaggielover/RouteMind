# R4-411B Google live validation preflight attempts

Contract: `a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`

This append-only record preserves two bounded point-call attempts made before
the final evidence writer was hardened. No provider payload, header, API key,
or business identifier is retained.

- Attempt 1: one `ComputeRoutes` request reached the provider boundary. The
  runner terminated with non-sensitive `TypeError` while aggregating an
  optional distance field; no aggregate artifact was produced.
- Attempt 2: one `ComputeRoutes` request returned HTTP success and was observed
  by the diagnostic harness; the temporary diagnostic process did not persist
  an artifact.
- Persisted usage before the final bounded run: 2 point requests, 0 matrix
  requests, 0 matrix elements.

These attempts are retained as execution history and do not constitute a
production, Japan-region, or Matrix entitlement claim.
