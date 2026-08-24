from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

from routemind_compute.application.artifacts import (
    DataArtifactManifest,
    DataRootArtifactAdapter,
)

LicenseStatus = Literal[
    "EXPLICIT_RESEARCH_USE",
    "PUBLIC_BENCHMARK_NO_EXPLICIT_LICENSE",
    "REVIEW_REQUIRED",
]
ReferenceStatus = Literal["PROVEN_OPTIMUM", "BEST_KNOWN", "REPORTED"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_INTEGER = re.compile(r"^[+-]?\d+$")
_LICENSE_STATUSES = {
    "EXPLICIT_RESEARCH_USE",
    "PUBLIC_BENCHMARK_NO_EXPLICIT_LICENSE",
    "REVIEW_REQUIRED",
}
_REFERENCE_STATUSES = {"PROVEN_OPTIMUM", "BEST_KNOWN", "REPORTED"}


class PublicBenchmarkError(ValueError):
    """Raised when public benchmark provenance or syntax is invalid."""


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validate_https(value: str, label: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise PublicBenchmarkError(f"{label} must be an absolute HTTPS URL")


def _validate_utc(value: str) -> None:
    if not value.endswith("Z"):
        raise PublicBenchmarkError("retrieved_at_utc must end with Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PublicBenchmarkError("retrieved_at_utc must be an ISO-8601 timestamp") from exc
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise PublicBenchmarkError("retrieved_at_utc must be UTC")


@dataclass(frozen=True, slots=True)
class BenchmarkReferenceValue:
    reference_id: str
    instance_id: str
    reference_status: ReferenceStatus
    vehicle_count: int | None
    distance: float
    objective_semantics: str
    numeric_semantics: str
    source_url: str
    notes: str

    def __post_init__(self) -> None:
        if not self.reference_id.strip() or not self.instance_id.strip():
            raise PublicBenchmarkError("reference identity must not be blank")
        if self.reference_status not in _REFERENCE_STATUSES:
            raise PublicBenchmarkError("reference status is not supported")
        if self.vehicle_count is not None and (
            isinstance(self.vehicle_count, bool) or self.vehicle_count <= 0
        ):
            raise PublicBenchmarkError("reference vehicle_count must be positive when present")
        if not isfinite(self.distance) or self.distance < 0:
            raise PublicBenchmarkError("reference distance must be finite and non-negative")
        if not self.objective_semantics.strip() or not self.numeric_semantics.strip():
            raise PublicBenchmarkError("reference semantics must not be blank")
        if not self.notes.strip():
            raise PublicBenchmarkError("reference notes must not be blank")
        _validate_https(self.source_url, "reference source_url")

    def payload(self) -> dict[str, object]:
        return {
            "reference_id": self.reference_id,
            "instance_id": self.instance_id,
            "reference_status": self.reference_status,
            "vehicle_count": self.vehicle_count,
            "distance": self.distance,
            "objective_semantics": self.objective_semantics,
            "numeric_semantics": self.numeric_semantics,
            "source_url": self.source_url,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class PublicBenchmarkSourceManifest:
    source_id: str
    family: str
    instance_id: str
    source_page_url: str
    download_url: str
    retrieved_at_utc: str
    license_status: LicenseStatus
    terms_url: str
    redistribution_allowed: bool
    distribution_sha256: str
    archive_member: str
    parser_id: str
    parser_version: str
    artifact: DataArtifactManifest
    references: tuple[BenchmarkReferenceValue, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_id, "source_id"),
            (self.family, "family"),
            (self.instance_id, "instance_id"),
            (self.archive_member, "archive_member"),
            (self.parser_id, "parser_id"),
            (self.parser_version, "parser_version"),
        ):
            if not value.strip():
                raise PublicBenchmarkError(f"{label} must not be blank")
        _validate_https(self.source_page_url, "source_page_url")
        _validate_https(self.download_url, "download_url")
        _validate_https(self.terms_url, "terms_url")
        _validate_utc(self.retrieved_at_utc)
        if self.license_status not in _LICENSE_STATUSES:
            raise PublicBenchmarkError("license_status is not supported")
        if not _SHA256.fullmatch(self.distribution_sha256):
            raise PublicBenchmarkError("distribution_sha256 must be a lowercase SHA-256 digest")
        if self.archive_member.startswith(("/", "\\")) or "\\" in self.archive_member:
            raise PublicBenchmarkError("archive_member must be a relative POSIX path")
        if any(part in {"", ".."} for part in self.archive_member.split("/")):
            raise PublicBenchmarkError("archive_member path is unsafe")
        if self.artifact.artifact_type != "benchmark":
            raise PublicBenchmarkError("public benchmark artifact_type must be benchmark")
        if len({item.reference_id for item in self.references}) != len(self.references):
            raise PublicBenchmarkError("reference identifiers must be unique")
        object.__setattr__(
            self, "references", tuple(sorted(self.references, key=lambda item: item.reference_id))
        )

    @property
    def digest(self) -> str:
        return _digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "public-benchmark-source-v1",
            "source_id": self.source_id,
            "family": self.family,
            "instance_id": self.instance_id,
            "source_page_url": self.source_page_url,
            "download_url": self.download_url,
            "retrieved_at_utc": self.retrieved_at_utc,
            "license_status": self.license_status,
            "terms_url": self.terms_url,
            "redistribution_allowed": self.redistribution_allowed,
            "distribution_sha256": self.distribution_sha256,
            "archive_member": self.archive_member,
            "parser_id": self.parser_id,
            "parser_version": self.parser_version,
            "artifact": self.artifact.payload(),
            "references": [item.payload() for item in self.references],
        }


@dataclass(frozen=True, slots=True)
class CartesianPoint:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise PublicBenchmarkError("Cartesian coordinates must be finite")


@dataclass(frozen=True, slots=True)
class CanonicalVrptwNode:
    node_id: int
    point: CartesianPoint
    demand: float
    ready_time: float
    due_time: float
    service_time: float

    def __post_init__(self) -> None:
        if isinstance(self.node_id, bool) or self.node_id < 0:
            raise PublicBenchmarkError("node_id must be a non-negative integer")
        for value, label in (
            (self.demand, "demand"),
            (self.ready_time, "ready_time"),
            (self.due_time, "due_time"),
            (self.service_time, "service_time"),
        ):
            if not isfinite(value) or value < 0:
                raise PublicBenchmarkError(f"{label} must be finite and non-negative")
        if self.due_time < self.ready_time:
            raise PublicBenchmarkError("node time window must be ordered")

    def payload(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "x": self.point.x,
            "y": self.point.y,
            "demand": self.demand,
            "ready_time": self.ready_time,
            "due_time": self.due_time,
            "service_time": self.service_time,
        }


@dataclass(frozen=True, slots=True)
class CanonicalVrptwInstance:
    instance_id: str
    max_vehicles: int
    vehicle_capacity: float
    depot: CanonicalVrptwNode
    customers: tuple[CanonicalVrptwNode, ...]
    distance_semantics: str = "EUCLIDEAN_DOUBLE"
    travel_time_semantics: str = "DISTANCE_EQUALS_TRAVEL_TIME"
    objective_semantics: str = "HIERARCHICAL_VEHICLES_THEN_DISTANCE"

    def __post_init__(self) -> None:
        if not self.instance_id.strip():
            raise PublicBenchmarkError("instance_id must not be blank")
        if isinstance(self.max_vehicles, bool) or self.max_vehicles <= 0:
            raise PublicBenchmarkError("max_vehicles must be positive")
        if not isfinite(self.vehicle_capacity) or self.vehicle_capacity <= 0:
            raise PublicBenchmarkError("vehicle_capacity must be finite and positive")
        if self.depot.node_id != 0 or self.depot.demand != 0:
            raise PublicBenchmarkError("node 0 must be the zero-demand depot")
        if not self.customers:
            raise PublicBenchmarkError("at least one customer is required")
        node_ids = [self.depot.node_id, *(item.node_id for item in self.customers)]
        if len(node_ids) != len(set(node_ids)):
            raise PublicBenchmarkError("node identifiers must be unique")
        if any(item.demand <= 0 for item in self.customers):
            raise PublicBenchmarkError("customer demand must be positive")
        for value, label in (
            (self.distance_semantics, "distance_semantics"),
            (self.travel_time_semantics, "travel_time_semantics"),
            (self.objective_semantics, "objective_semantics"),
        ):
            if not value.strip():
                raise PublicBenchmarkError(f"{label} must not be blank")
        object.__setattr__(
            self, "customers", tuple(sorted(self.customers, key=lambda item: item.node_id))
        )

    @property
    def digest(self) -> str:
        return _digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "canonical-vrptw-v1",
            "instance_id": self.instance_id,
            "max_vehicles": self.max_vehicles,
            "vehicle_capacity": self.vehicle_capacity,
            "depot": self.depot.payload(),
            "customers": [item.payload() for item in self.customers],
            "distance_semantics": self.distance_semantics,
            "travel_time_semantics": self.travel_time_semantics,
            "objective_semantics": self.objective_semantics,
        }


@dataclass(frozen=True, slots=True)
class TransformationRecord:
    operation: str
    input_semantics: str
    output_semantics: str
    lossless: bool
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.operation.strip() or not self.input_semantics.strip():
            raise PublicBenchmarkError("transformation identity must not be blank")
        if not self.output_semantics.strip():
            raise PublicBenchmarkError("transformation output semantics must not be blank")
        keys = [key for key, _ in self.details]
        if any(not key.strip() for key in keys) or len(keys) != len(set(keys)):
            raise PublicBenchmarkError("transformation detail keys must be unique and non-blank")
        if any(not value.strip() for _, value in self.details):
            raise PublicBenchmarkError("transformation detail values must not be blank")
        object.__setattr__(self, "details", tuple(sorted(self.details)))

    def payload(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "input_semantics": self.input_semantics,
            "output_semantics": self.output_semantics,
            "lossless": self.lossless,
            "details": list(self.details),
        }


@dataclass(frozen=True, slots=True)
class ParsedPublicBenchmark:
    instance: CanonicalVrptwInstance
    source_manifest_digest: str
    artifact_sha256: str
    transformations: tuple[TransformationRecord, ...]

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.source_manifest_digest):
            raise PublicBenchmarkError("source manifest digest is invalid")
        if not _SHA256.fullmatch(self.artifact_sha256):
            raise PublicBenchmarkError("artifact sha256 is invalid")
        if not self.transformations:
            raise PublicBenchmarkError("at least one transformation record is required")

    @property
    def lineage_digest(self) -> str:
        return _digest(
            {
                "instance_digest": self.instance.digest,
                "source_manifest_digest": self.source_manifest_digest,
                "artifact_sha256": self.artifact_sha256,
                "transformations": [item.payload() for item in self.transformations],
            }
        )


class SolomonVrptwParser:
    parser_id = "solomon-vrptw-text"
    version = "1.0.0"

    def parse(self, payload: bytes, source: PublicBenchmarkSourceManifest) -> ParsedPublicBenchmark:
        if source.parser_id != self.parser_id or source.parser_version != self.version:
            raise PublicBenchmarkError("source manifest parser identity does not match parser")
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise PublicBenchmarkError("benchmark payload must be UTF-8 compatible text") from exc
        if "\x00" in text:
            raise PublicBenchmarkError("benchmark payload must not contain NUL bytes")
        instance = self._parse_text(text)
        if instance.instance_id.casefold() != source.instance_id.casefold():
            raise PublicBenchmarkError("parsed instance identity does not match source manifest")
        transformation = TransformationRecord(
            operation=f"{self.parser_id}:{self.version}",
            input_semantics="SOLOMON_INTEGER_TEXT",
            output_semantics="CANONICAL_VRPTW_V1_CARTESIAN",
            lossless=True,
            details=(
                ("coordinate_policy", "preserve Cartesian coordinates"),
                ("numeric_policy", "parse source integers as exact binary-safe values"),
                ("unit_policy", "preserve source units without scaling"),
            ),
        )
        return ParsedPublicBenchmark(
            instance=instance,
            source_manifest_digest=source.digest,
            artifact_sha256=sha256(payload).hexdigest(),
            transformations=(transformation,),
        )

    def _parse_text(self, text: str) -> CanonicalVrptwInstance:
        lines = [line.strip() for line in text.splitlines()]
        non_empty = [line for line in lines if line]
        if not non_empty:
            raise PublicBenchmarkError("benchmark payload is empty")
        instance_id = non_empty[0]
        upper = [line.upper() for line in lines]
        try:
            vehicle_index = upper.index("VEHICLE")
            customer_index = upper.index("CUSTOMER")
        except ValueError as exc:
            raise PublicBenchmarkError(
                "benchmark VEHICLE and CUSTOMER sections are required"
            ) from exc
        if vehicle_index >= customer_index:
            raise PublicBenchmarkError("benchmark sections are out of order")
        vehicle_values: tuple[int, int] | None = None
        for line in lines[vehicle_index + 1 : customer_index]:
            tokens = line.split()
            if len(tokens) == 2 and all(_INTEGER.fullmatch(token) for token in tokens):
                vehicle_values = (
                    int(tokens[0]),
                    int(tokens[1]),
                )
                break
        if vehicle_values is None:
            raise PublicBenchmarkError("vehicle count and capacity row is missing")
        rows: list[CanonicalVrptwNode] = []
        for line in lines[customer_index + 1 :]:
            tokens = line.split()
            if not tokens or not _INTEGER.fullmatch(tokens[0]):
                continue
            if len(tokens) != 7 or not all(_INTEGER.fullmatch(token) for token in tokens):
                raise PublicBenchmarkError("customer row must contain seven integer fields")
            values = tuple(int(token) for token in tokens)
            rows.append(
                CanonicalVrptwNode(
                    node_id=values[0],
                    point=CartesianPoint(float(values[1]), float(values[2])),
                    demand=float(values[3]),
                    ready_time=float(values[4]),
                    due_time=float(values[5]),
                    service_time=float(values[6]),
                )
            )
        depots = [item for item in rows if item.node_id == 0]
        if len(depots) != 1:
            raise PublicBenchmarkError("benchmark must contain exactly one depot row")
        return CanonicalVrptwInstance(
            instance_id=instance_id,
            max_vehicles=vehicle_values[0],
            vehicle_capacity=float(vehicle_values[1]),
            depot=depots[0],
            customers=tuple(item for item in rows if item.node_id != 0),
        )


def load_public_benchmark(
    source: PublicBenchmarkSourceManifest,
    adapter: DataRootArtifactAdapter,
    parser: SolomonVrptwParser | None = None,
) -> ParsedPublicBenchmark:
    resolved = adapter.resolve(source.artifact)
    selected = parser or SolomonVrptwParser()
    parsed = selected.parse(resolved.path.read_bytes(), source)
    if parsed.artifact_sha256 != resolved.actual_sha256:
        raise PublicBenchmarkError("parsed payload checksum differs from resolved artifact")
    return parsed


def load_public_benchmark_source_manifest(path: Path) -> PublicBenchmarkSourceManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicBenchmarkError("public benchmark source manifest is unreadable") from exc
    root = _mapping(payload, "manifest")
    if _string(root, "schema_version") != "public-benchmark-source-v1":
        raise PublicBenchmarkError("public benchmark source schema version is unsupported")
    artifact_payload = _mapping(root.get("artifact"), "artifact")
    configuration = tuple(
        (_sequence_string(item, 0, "configuration"), _sequence_string(item, 1, "configuration"))
        for item in _sequence(artifact_payload.get("configuration"), "configuration")
    )
    artifact = DataArtifactManifest(
        artifact_id=_string(artifact_payload, "artifact_id"),
        artifact_type=_string(artifact_payload, "artifact_type"),
        relative_path=_string(artifact_payload, "relative_path"),
        sha256=_string(artifact_payload, "sha256"),
        producer=_string(artifact_payload, "producer"),
        revision=_string(artifact_payload, "revision"),
        configuration=configuration,
        seed=_integer_value(artifact_payload, "seed"),
    )
    references = tuple(
        _reference_from_payload(item) for item in _sequence(root.get("references"), "references")
    )
    license_status = _string(root, "license_status")
    if license_status not in _LICENSE_STATUSES:
        raise PublicBenchmarkError("license_status is not supported")
    return PublicBenchmarkSourceManifest(
        source_id=_string(root, "source_id"),
        family=_string(root, "family"),
        instance_id=_string(root, "instance_id"),
        source_page_url=_string(root, "source_page_url"),
        download_url=_string(root, "download_url"),
        retrieved_at_utc=_string(root, "retrieved_at_utc"),
        license_status=cast(LicenseStatus, license_status),
        terms_url=_string(root, "terms_url"),
        redistribution_allowed=_boolean(root, "redistribution_allowed"),
        distribution_sha256=_string(root, "distribution_sha256"),
        archive_member=_string(root, "archive_member"),
        parser_id=_string(root, "parser_id"),
        parser_version=_string(root, "parser_version"),
        artifact=artifact,
        references=references,
    )


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PublicBenchmarkError(f"{label} must be an object")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise PublicBenchmarkError(f"{label} must be an array")
    return cast(Sequence[object], value)


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PublicBenchmarkError(f"{key} must be a non-blank string")
    return value


def _boolean(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise PublicBenchmarkError(f"{key} must be a boolean")
    return value


def _integer_value(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PublicBenchmarkError(f"{key} must be an integer")
    return value


def _number(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PublicBenchmarkError(f"{key} must be numeric")
    return float(value)


def _sequence_string(value: object, index: int, label: str) -> str:
    sequence = _sequence(value, label)
    if len(sequence) != 2 or not isinstance(sequence[index], str):
        raise PublicBenchmarkError(f"{label} entries must be string pairs")
    result = cast(str, sequence[index])
    if not result.strip():
        raise PublicBenchmarkError(f"{label} entries must not be blank")
    return result


def _reference_from_payload(value: object) -> BenchmarkReferenceValue:
    payload = _mapping(value, "reference")
    status = _string(payload, "reference_status")
    if status not in _REFERENCE_STATUSES:
        raise PublicBenchmarkError("reference status is not supported")
    return BenchmarkReferenceValue(
        reference_id=_string(payload, "reference_id"),
        instance_id=_string(payload, "instance_id"),
        reference_status=cast(ReferenceStatus, status),
        vehicle_count=_optional_integer(payload, "vehicle_count"),
        distance=_number(payload, "distance"),
        objective_semantics=_string(payload, "objective_semantics"),
        numeric_semantics=_string(payload, "numeric_semantics"),
        source_url=_string(payload, "source_url"),
        notes=_string(payload, "notes"),
    )


def _optional_integer(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PublicBenchmarkError(f"{key} must be an integer or null")
    return value
