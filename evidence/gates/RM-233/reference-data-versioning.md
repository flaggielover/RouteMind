# RM-233 Reference Data Versioning Evidence

Date: 2026-08-24
Status: validating

## Scope

- Python owns an immutable, content-addressed `ReferenceDataIdentity` and
  in-process catalog for travel, zone, strategy, and analytical reference data.
- Re-registration with changed content is rejected; additive versions require
  an explicit superseded identity.
- Scenario/replay and RouteBench manifests carry `reference_data_id`; verified
  external artifacts expose the same stable identity, and existing archive/mart
  records retain their reference-data link.

## Local evidence

- Compute `scripts/compute-api.ps1 check`: PASS - 212 tests, 95.17% coverage,
  contract validation (6 schemas / 18 fixtures), determinism, archive, mart,
  and semantic-metric gates.
- Reference-data tests cover stable identity links and content digests,
  immutable conflict rejection, additive supersession, invalid values, replay
  manifest identity, benchmark manifest identity, and external artifact
  metadata identity.
- The implementation preserves Java's existing durable dispatch ledger
  `reference_data_id` and the analytical archive/mart `reference_data_id`
  columns; no new source of business truth was introduced.

## Remote evidence

Pending checkpoint commit and GitHub Actions run.

## Boundaries

Large payloads remain under the external `ROUTEMIND_DATA_ROOT` boundary. The
catalog stores identities and digests only; it does not copy, rewrite, or serve
large travel/zone datasets.
