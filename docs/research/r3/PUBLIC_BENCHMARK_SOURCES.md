# Round 3 Public Benchmark Sources

Reviewed: 2026-08-24 (Asia/Shanghai)

## Primary sources

- M. M. Solomon, "Algorithms for the Vehicle Routing and Scheduling Problems
  with Time Window Constraints," *Operations Research* 35(2), 1987,
  https://doi.org/10.1287/opre.35.2.254.
- SINTEF VRPTW format documentation:
  https://www.sintef.no/projectweb/top/vrptw/documentation2/.
- SINTEF Solomon benchmark and 100-customer catalog:
  https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/ and
  https://www.sintef.no/projectweb/top/vrptw/100-customers/.
- SINTEF Gehring-Homberger catalog:
  https://www.sintef.no/projectweb/top/vrptw/homberger-benchmark/.
- CVRPLIB VRPTW catalog and current terms:
  https://galgos.inf.puc-rio.br/cvrplib/en/instances/2 and
  https://galgos.inf.puc-rio.br/cvrplib/en/register/terms.

## Semantics frozen for adapters

The source format uses customer `0` as the depot, declares maximum vehicle count
and homogeneous capacity, and defines ready/due time as the interval in which
service may start. Euclidean distance equals travel time. Canonical parsing keeps
source Cartesian coordinates and source units. It does not construct RouteMind
`GeoPoint` values or invoke the geographic travel provider.

SINTEF's reported objective is hierarchical: first minimize vehicle count, then
distance using double precision. SINTEF explicitly warns that monolithic-distance
or lower-precision results are not necessarily comparable. The manifest retains
the SINTEF and CVRPLIB C101 references separately instead of selecting the more
favorable value.

## Licensing and storage disposition

CVRPLIB's December 2025 terms permit research, academic, and challenge use and
warn that redistribution can have dataset-specific terms. The reviewed SINTEF
download page publishes the benchmark archive but exposes no explicit data
license. RouteMind therefore records
`PUBLIC_BENCHMARK_NO_EXPLICIT_LICENSE`, sets redistribution to false, stores the
archive and extracted member only under `ROUTEMIND_DATA_ROOT`, and commits only
source URLs, checksums, metadata, and a synthetic parser fixture. Any broader
redistribution or paid use remains outside the authorized scope.

The source manifest is
`docs/research/r3/manifests/public-benchmarks/solomon-c101-source.json`. The
distribution and member checksums are immutable input identities, not evidence
of solver quality.
