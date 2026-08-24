# R3-310 Public Benchmark Adapter Evidence

Date: 2026-08-24 (Asia/Shanghai)
Status: validating
Scientific gates: E-IN-PROGRESS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE

## Scope and non-claims

This task establishes public benchmark provenance, parsing, and lineage controls.
It runs no solver comparison and supports no claim about feasibility rate,
solution quality, optimality, scale, superiority, or novelty.

## Source and license review

Primary source review is recorded in
`docs/research/r3/PUBLIC_BENCHMARK_SOURCES.md`. The sources are Solomon's 1987
INFORMS paper, SINTEF's VRPTW documentation and benchmark catalogs, and CVRPLIB's
catalog and December 2025 terms.

SINTEF defines Cartesian coordinates, depot `0`, maximum vehicle count, capacity,
service-start windows, and distance-equals-time semantics. Its catalog uses a
hierarchical vehicles-then-distance objective with double precision and warns
against direct comparison with monolithic or low-precision values. CVRPLIB permits
research use but warns that redistribution can have dataset-specific terms.
RouteMind therefore stores real files only in `ROUTEMIND_DATA_ROOT`, records
redistribution as false, and commits only metadata, checksums, and a synthetic
fixture.

The AnySearch Python client was unavailable because its local `requests`
dependency was absent; the documented Node fallback reached an AnySearch server
that did not expose `list_domains`. Research continued through the built-in web
search, restricted to the primary sources above. This tool failure did not change
source selection or create an empirical claim.

## Engineering controls

- `public_benchmarks.py` defines immutable source, reference, Cartesian node,
  canonical instance, transformation, and parsed-lineage contracts.
- Source manifests require absolute HTTPS URLs, UTC retrieval time, explicit
  license status, archive/member identities, SHA-256 values, parser identity,
  safe POSIX paths, and distinct reference IDs.
- Loading reuses `DataRootArtifactAdapter`, including root escape and checksum
  rejection, before any parse occurs.
- The Solomon parser fails closed on missing/reordered sections, invalid rows,
  encoding or NUL data, depot errors, identity drift, and parser-version drift.
- No conversion to RouteMind geographic `GeoPoint` occurs. Source Cartesian
  coordinates and units remain unchanged.
- Conflicting SINTEF/CVRPLIB C101 values coexist with their own objective and
  numeric semantics. Neither is called ground truth by this task.

## Immutable external input

```text
ROUTEMIND_DATA_ROOT relative archive:
datasets/public-benchmarks/solomon/solomon-100.zip
bytes: 83546
sha256: 8a0a72cbe6b7f8f9988ace4ebde0378ec34943acaaac47f2c408915e41887747

archive member: In/c101.txt
bytes: 7523
sha256: a6da75152d182d60ecd2c6f854296f5be452f92282d096adebcf5d99a7f16516
```

The committed manifest digest is
`5f850daa1b56bc9634ded08b1f7763ab0ad38c10160955c01e7bdc185cc374cb`.

## Executable evidence

The synthetic fixture suite passed 28 tests after the committed-manifest check
was added. Strict Ruff and mypy checks passed. The full compute gate initially
ran 244 passing tests but correctly rejected 94.08% global coverage. The coverage
threshold was not changed; additional negative-path tests plus the committed
manifest check raised the final accepted run to 264 passing tests and 95.55%
coverage. Contract validation passed 6 schemas and 18 fixtures, followed by
deterministic scenario, archive, DuckDB mart, and semantic-metric gates. The full
available repository gate also passed Java 80/80 and Web 34 files / 92 tests plus
the production build.

A real external-data loader probe produced:

```text
instance: C101
customers: 100
max vehicles: 25
capacity: 200.0
instance digest: 4aaf1b4d45d222eee865014ef29fff58fabc563dc22ef3caf131577789a4171e
lineage digest: 3f78d911431aa728717d37bcea2f3ff5cf65138c1162deda5d34abd92c4e4ce2
references: CVRPLIB reported 827.3; SINTEF best-known 10 vehicles / 828.94
```

This probe validates parsing and lineage only. Repository gates and GitHub
Actions remain required before E-PASS.
