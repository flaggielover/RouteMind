# RM-142 Data-Root Matrix and Artifact Adapter

Date: 2026-08-22

## Implemented contract

- `DataArtifactManifest` records artifact type, relative path, SHA-256,
  producer, revision, canonical configuration, and seed with a stable digest.
- `DataRootArtifactAdapter` resolves artifacts from `ROUTEMIND_DATA_ROOT` (or an
  explicit root) without copying payloads into the repository and verifies the
  content checksum before returning a path.
- Relative POSIX paths are required; absolute paths, Windows drive paths,
  traversal, missing roots, missing payloads, and checksum mismatches fail
  closed with explicit errors. Resolved paths are checked after symlink-aware
  normalization against the data root.

## Evidence

- Compute check passes 85 tests at 95.22% coverage, including manifest
  canonicalization, external-root resolution, environment configuration,
  missing/corrupt payload handling, and unsafe path rejection.
- Full available gate passes Java 60 tests, Python 85 tests at 95.22%, Web 38
  unit tests/build, and 5 schemas/15 fixtures.
- No generated matrix, graph, replay, or other large artifact is committed to
  the repository.

## Gate decision

Local L1 data-root, L2 artifact-manifest, and security evidence is complete.
Remote Actions run `32578382074` passed all five jobs; RM-142 is fully
validated.
