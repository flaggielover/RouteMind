from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.artifacts import (
    ArtifactResolutionError,
    DataArtifactManifest,
    DataRootArtifactAdapter,
)
from routemind_compute.application.public_benchmarks import (
    BenchmarkReferenceValue,
    CanonicalVrptwInstance,
    CanonicalVrptwNode,
    CartesianPoint,
    LicenseStatus,
    ParsedPublicBenchmark,
    PublicBenchmarkError,
    PublicBenchmarkSourceManifest,
    ReferenceStatus,
    SolomonVrptwParser,
    TransformationRecord,
    load_public_benchmark,
    load_public_benchmark_source_manifest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "public_benchmarks" / "solomon-tiny.txt"
SOURCE_MANIFEST = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "public-benchmarks"
    / "solomon-c101-source.json"
)


def reference_for(**overrides: object) -> BenchmarkReferenceValue:
    values: dict[str, object] = {
        "reference_id": "fixture-tiny101-reported-v1",
        "instance_id": "TINY101",
        "reference_status": "REPORTED",
        "vehicle_count": 1,
        "distance": 20.0,
        "objective_semantics": "HIERARCHICAL_VEHICLES_THEN_DISTANCE",
        "numeric_semantics": "EUCLIDEAN_DOUBLE",
        "source_url": "https://example.test/routemind/fixtures/solomon-tiny",
        "notes": "Synthetic parser fixture; not a public benchmark result.",
    }
    values.update(overrides)
    return BenchmarkReferenceValue(**values)  # type: ignore[arg-type]


def source_for(
    payload: bytes, relative_path: str = "benchmarks/solomon-tiny.txt"
) -> PublicBenchmarkSourceManifest:
    artifact = DataArtifactManifest(
        artifact_id="solomon-tiny101",
        artifact_type="benchmark",
        relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(),
        producer="RouteMind test fixture",
        revision="fixture-v1",
        configuration=(("format", "solomon-vrptw-text"),),
        seed=0,
    )
    reference = reference_for()
    return PublicBenchmarkSourceManifest(
        source_id="solomon-tiny101-source-v1",
        family="SOLOMON_VRPTW_FIXTURE",
        instance_id="TINY101",
        source_page_url="https://example.test/routemind/fixtures",
        download_url="https://example.test/routemind/fixtures/solomon-tiny.txt",
        retrieved_at_utc="2026-08-24T05:00:00Z",
        license_status="EXPLICIT_RESEARCH_USE",
        terms_url="https://example.test/routemind/fixtures/terms",
        redistribution_allowed=True,
        distribution_sha256=artifact.sha256,
        archive_member="solomon-tiny.txt",
        parser_id=SolomonVrptwParser.parser_id,
        parser_version=SolomonVrptwParser.version,
        artifact=artifact,
        references=(reference,),
    )


def test_solomon_parser_preserves_cartesian_and_time_window_semantics() -> None:
    payload = FIXTURE.read_bytes()
    parsed = SolomonVrptwParser().parse(payload, source_for(payload))

    assert parsed.instance.instance_id == "TINY101"
    assert parsed.instance.max_vehicles == 2
    assert parsed.instance.vehicle_capacity == 10
    assert parsed.instance.depot.point.x == 0
    assert tuple(item.node_id for item in parsed.instance.customers) == (1, 2)
    assert parsed.instance.customers[0].point.x == 3
    assert parsed.instance.customers[0].point.y == 4
    assert parsed.instance.customers[1].ready_time == 10
    assert parsed.instance.distance_semantics == "EUCLIDEAN_DOUBLE"
    assert parsed.transformations[0].lossless is True
    assert dict(parsed.transformations[0].details)["unit_policy"] == (
        "preserve source units without scaling"
    )
    assert len(parsed.instance.digest) == 64
    assert len(parsed.lineage_digest) == 64


def test_data_root_loader_verifies_checksum_before_parsing(tmp_path: Path) -> None:
    payload = FIXTURE.read_bytes()
    target = tmp_path / "benchmarks" / "solomon-tiny.txt"
    target.parent.mkdir()
    target.write_bytes(payload)
    source = source_for(payload)

    parsed = load_public_benchmark(source, DataRootArtifactAdapter(tmp_path))

    assert parsed.artifact_sha256 == source.artifact.sha256
    target.write_bytes(payload + b"\nchanged")
    with pytest.raises(ArtifactResolutionError, match="checksum mismatch"):
        load_public_benchmark(source, DataRootArtifactAdapter(tmp_path))


def test_source_manifest_round_trips_and_retains_reference_semantics(tmp_path: Path) -> None:
    payload = FIXTURE.read_bytes()
    source = source_for(payload)
    manifest_path = tmp_path / "source.json"
    manifest_path.write_text(json.dumps(source.payload()), encoding="utf-8")

    loaded = load_public_benchmark_source_manifest(manifest_path)

    assert loaded == source
    assert loaded.digest == source.digest
    assert loaded.references[0].reference_status == "REPORTED"
    assert loaded.references[0].objective_semantics == ("HIERARCHICAL_VEHICLES_THEN_DISTANCE")


def test_committed_solomon_source_manifest_is_valid_without_loading_large_data() -> None:
    source = load_public_benchmark_source_manifest(SOURCE_MANIFEST)

    assert source.instance_id == "C101"
    assert source.redistribution_allowed is False
    assert source.license_status == "PUBLIC_BENCHMARK_NO_EXPLICIT_LICENSE"
    assert source.distribution_sha256 == (
        "8a0a72cbe6b7f8f9988ace4ebde0378ec34943acaaac47f2c408915e41887747"
    )
    assert source.artifact.sha256 == (
        "a6da75152d182d60ecd2c6f854296f5be452f92282d096adebcf5d99a7f16516"
    )
    assert {item.reference_id for item in source.references} == {
        "cvrplib-c101-catalog-2026-08-24",
        "sintef-c101-hierarchical-double-2026-08-24",
    }


@pytest.mark.parametrize(
    "replacement, message, expected",
    [
        ("CUSTOMER", "missing", "VEHICLE and CUSTOMER"),
        (
            "  0          0          0          0          0        100          0",
            "missing",
            "exactly one depot",
        ),
        (
            "  1          3          4          4          0         50          5",
            "  1 3 4",
            "seven integer fields",
        ),
    ],
)
def test_solomon_parser_fails_closed_on_malformed_sections(
    replacement: str, message: str, expected: str
) -> None:
    original = FIXTURE.read_text(encoding="utf-8")
    malformed = original.replace(replacement, message, 1).encode()
    source = source_for(malformed)

    with pytest.raises(PublicBenchmarkError, match=expected):
        SolomonVrptwParser().parse(malformed, source)


def test_source_manifest_rejects_unsafe_or_ambiguous_provenance() -> None:
    payload = FIXTURE.read_bytes()
    valid = source_for(payload)
    values = {field: getattr(valid, field) for field in valid.__dataclass_fields__}
    for field, bad_value in (
        ("source_page_url", "http://example.test/source"),
        ("retrieved_at_utc", "2026-08-24"),
        ("distribution_sha256", "unknown"),
        ("archive_member", "../fixture.txt"),
    ):
        candidate = {**values, field: bad_value}
        with pytest.raises(PublicBenchmarkError):
            PublicBenchmarkSourceManifest(**candidate)


def test_parser_rejects_manifest_identity_and_parser_drift() -> None:
    payload = FIXTURE.read_bytes()
    valid = source_for(payload)
    values = {field: getattr(valid, field) for field in valid.__dataclass_fields__}
    wrong_instance = PublicBenchmarkSourceManifest(**{**values, "instance_id": "OTHER"})
    wrong_parser = PublicBenchmarkSourceManifest(**{**values, "parser_version": "2.0.0"})

    with pytest.raises(PublicBenchmarkError, match="instance identity"):
        SolomonVrptwParser().parse(payload, wrong_instance)
    with pytest.raises(PublicBenchmarkError, match="parser identity"):
        SolomonVrptwParser().parse(payload, wrong_parser)


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"reference_id": " "}, "identity"),
        ({"reference_status": cast(ReferenceStatus, "UNKNOWN")}, "status"),
        ({"vehicle_count": 0}, "vehicle_count"),
        ({"vehicle_count": True}, "vehicle_count"),
        ({"distance": float("nan")}, "distance"),
        ({"objective_semantics": " "}, "semantics"),
        ({"numeric_semantics": " "}, "semantics"),
        ({"notes": " "}, "notes"),
        ({"source_url": "http://example.test/reference"}, "HTTPS"),
    ],
)
def test_reference_contract_rejects_ambiguous_values(
    overrides: dict[str, object], expected: str
) -> None:
    with pytest.raises(PublicBenchmarkError, match=expected):
        reference_for(**overrides)


def test_reference_contract_allows_explicitly_missing_vehicle_count() -> None:
    reference = reference_for(vehicle_count=None)

    assert reference.vehicle_count is None
    assert reference.payload()["vehicle_count"] is None


def test_source_contract_rejects_all_provenance_failure_classes() -> None:
    payload = FIXTURE.read_bytes()
    valid = source_for(payload)
    values = {field: getattr(valid, field) for field in valid.__dataclass_fields__}
    dataset_artifact = replace(valid.artifact, artifact_type="dataset")
    duplicate_references = (valid.references[0], valid.references[0])
    for field, bad_value, expected in (
        ("source_id", " ", "source_id"),
        ("download_url", "not-a-url", "HTTPS"),
        ("terms_url", "http://example.test/terms", "HTTPS"),
        ("retrieved_at_utc", "badZ", "ISO-8601"),
        ("license_status", cast(LicenseStatus, "UNKNOWN"), "license_status"),
        ("archive_member", "/absolute.txt", "relative POSIX"),
        ("archive_member", "dir\\member.txt", "relative POSIX"),
        ("archive_member", "dir//member.txt", "unsafe"),
        ("artifact", dataset_artifact, "artifact_type"),
        ("references", duplicate_references, "reference identifiers"),
    ):
        with pytest.raises(PublicBenchmarkError, match=expected):
            PublicBenchmarkSourceManifest(**{**values, field: bad_value})


def node_for(node_id: int, demand: float = 1, **overrides: object) -> CanonicalVrptwNode:
    values: dict[str, object] = {
        "node_id": node_id,
        "point": CartesianPoint(1, 2),
        "demand": demand,
        "ready_time": 0,
        "due_time": 10,
        "service_time": 1,
    }
    values.update(overrides)
    return CanonicalVrptwNode(**values)  # type: ignore[arg-type]


def canonical_for(**overrides: object) -> CanonicalVrptwInstance:
    values: dict[str, object] = {
        "instance_id": "TINY101",
        "max_vehicles": 2,
        "vehicle_capacity": 10,
        "depot": node_for(0, demand=0),
        "customers": (node_for(1),),
    }
    values.update(overrides)
    return CanonicalVrptwInstance(**values)  # type: ignore[arg-type]


def test_canonical_nodes_reject_invalid_numeric_semantics() -> None:
    for factory, expected in (
        (lambda: CartesianPoint(float("inf"), 0), "coordinates"),
        (lambda: CartesianPoint(0, float("nan")), "coordinates"),
        (lambda: node_for(-1), "node_id"),
        (lambda: node_for(True), "node_id"),
        (lambda: node_for(1, demand=-1), "demand"),
        (lambda: node_for(1, ready_time=-1), "ready_time"),
        (lambda: node_for(1, due_time=float("inf")), "due_time"),
        (lambda: node_for(1, service_time=-1), "service_time"),
        (lambda: node_for(1, ready_time=5, due_time=4), "ordered"),
    ):
        with pytest.raises(PublicBenchmarkError, match=expected):
            factory()


def test_canonical_instance_rejects_invalid_problem_semantics() -> None:
    customer = node_for(1)
    for overrides, expected in (
        ({"instance_id": " "}, "instance_id"),
        ({"max_vehicles": 0}, "max_vehicles"),
        ({"max_vehicles": True}, "max_vehicles"),
        ({"vehicle_capacity": float("nan")}, "vehicle_capacity"),
        ({"depot": node_for(2, demand=0)}, "zero-demand depot"),
        ({"depot": node_for(0, demand=1)}, "zero-demand depot"),
        ({"customers": ()}, "at least one"),
        ({"customers": (customer, customer)}, "identifiers"),
        ({"customers": (node_for(1, demand=0),)}, "demand"),
        ({"distance_semantics": " "}, "distance_semantics"),
        ({"travel_time_semantics": " "}, "travel_time_semantics"),
        ({"objective_semantics": " "}, "objective_semantics"),
    ):
        with pytest.raises(PublicBenchmarkError, match=expected):
            canonical_for(**overrides)


def test_canonical_instance_orders_customers_deterministically() -> None:
    instance = canonical_for(customers=(node_for(2), node_for(1)))

    assert tuple(item.node_id for item in instance.customers) == (1, 2)
    assert instance.payload()["schema_version"] == "canonical-vrptw-v1"


def test_transformation_and_parsed_lineage_contracts_fail_closed() -> None:
    for overrides, expected in (
        ({"operation": " "}, "identity"),
        ({"input_semantics": " "}, "identity"),
        ({"output_semantics": " "}, "output semantics"),
        ({"details": (("", "value"),)}, "detail keys"),
        ({"details": (("key", "a"), ("key", "b"))}, "detail keys"),
        ({"details": (("key", " "),)}, "detail values"),
    ):
        values = {
            "operation": "parse",
            "input_semantics": "input",
            "output_semantics": "output",
            "lossless": True,
            "details": (("key", "value"),),
            **overrides,
        }
        with pytest.raises(PublicBenchmarkError, match=expected):
            TransformationRecord(**values)  # type: ignore[arg-type]

    transformation = TransformationRecord("parse", "input", "output", True)
    for source_digest, artifact_digest, transformations, expected in (
        ("bad", "0" * 64, (transformation,), "source manifest"),
        ("0" * 64, "bad", (transformation,), "artifact sha256"),
        ("0" * 64, "0" * 64, (), "at least one"),
    ):
        with pytest.raises(PublicBenchmarkError, match=expected):
            ParsedPublicBenchmark(canonical_for(), source_digest, artifact_digest, transformations)


def test_parser_rejects_encoding_nul_empty_order_and_missing_vehicle_row() -> None:
    valid_payload = FIXTURE.read_bytes()
    cases = (
        (b"\xff", "UTF-8"),
        (valid_payload + b"\x00", "NUL"),
        (b" \n", "empty"),
        (b"TINY101\nCUSTOMER\nVEHICLE\n", "out of order"),
        (b"TINY101\nVEHICLE\nNUMBER CAPACITY\nCUSTOMER\n", "vehicle count"),
    )
    for malformed, expected in cases:
        with pytest.raises(PublicBenchmarkError, match=expected):
            SolomonVrptwParser().parse(malformed, source_for(malformed))


def test_loader_rejects_parser_checksum_deception(tmp_path: Path) -> None:
    payload = FIXTURE.read_bytes()
    target = tmp_path / "benchmarks" / "solomon-tiny.txt"
    target.parent.mkdir()
    target.write_bytes(payload)
    source = source_for(payload)

    class MismatchingParser(SolomonVrptwParser):
        def parse(
            self, candidate: bytes, manifest: PublicBenchmarkSourceManifest
        ) -> ParsedPublicBenchmark:
            parsed = super().parse(candidate, manifest)
            return replace(parsed, artifact_sha256="0" * 64)

    with pytest.raises(PublicBenchmarkError, match="checksum differs"):
        load_public_benchmark(source, DataRootArtifactAdapter(tmp_path), MismatchingParser())


def write_manifest(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "manifest.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_manifest_loader_rejects_unreadable_schema_and_root_types(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(PublicBenchmarkError, match="unreadable"):
        load_public_benchmark_source_manifest(missing)
    with pytest.raises(PublicBenchmarkError, match="unreadable"):
        load_public_benchmark_source_manifest(write_manifest(tmp_path, "{"))
    with pytest.raises(PublicBenchmarkError, match="object"):
        load_public_benchmark_source_manifest(write_manifest(tmp_path, []))

    source_payload = source_for(FIXTURE.read_bytes()).payload()
    with pytest.raises(PublicBenchmarkError, match="schema version"):
        load_public_benchmark_source_manifest(
            write_manifest(tmp_path, {**source_payload, "schema_version": "future"})
        )


def test_manifest_loader_rejects_structural_type_drift(tmp_path: Path) -> None:
    base = source_for(FIXTURE.read_bytes()).payload()
    artifact = cast(dict[str, object], base["artifact"])
    reference = cast(list[dict[str, object]], base["references"])[0]
    cases: tuple[tuple[object, str], ...] = (
        ({**base, "artifact": []}, "artifact must be an object"),
        ({**base, "references": {}}, "references must be an array"),
        ({**base, "redistribution_allowed": "yes"}, "must be a boolean"),
        ({**base, "license_status": "UNKNOWN"}, "license_status"),
        ({**base, "source_id": 7}, "non-blank string"),
        ({**base, "artifact": {**artifact, "seed": True}}, "seed must be an integer"),
        (
            {**base, "artifact": {**artifact, "configuration": ["bad"]}},
            "configuration must be an array",
        ),
        (
            {**base, "artifact": {**artifact, "configuration": [["only-one"]]}},
            "string pairs",
        ),
        (
            {**base, "artifact": {**artifact, "configuration": [["", "value"]]}},
            "must not be blank",
        ),
        (
            {**base, "references": [{**reference, "reference_status": "UNKNOWN"}]},
            "reference status",
        ),
        (
            {**base, "references": [{**reference, "distance": True}]},
            "distance must be numeric",
        ),
        (
            {**base, "references": [{**reference, "vehicle_count": "one"}]},
            "vehicle_count must be an integer or null",
        ),
    )
    for payload, expected in cases:
        with pytest.raises(PublicBenchmarkError, match=expected):
            load_public_benchmark_source_manifest(write_manifest(tmp_path, payload))
