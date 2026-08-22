from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

Metadata = tuple[tuple[str, str], ...]
RecoveryService = Literal["postgres", "rabbitmq", "redis"]
RecoveryFormat = Literal["pg_dump", "rabbitmq-definitions", "redis-rdb"]

SERVICES: tuple[RecoveryService, ...] = ("postgres", "rabbitmq", "redis")
FORMATS: tuple[RecoveryFormat, ...] = ("pg_dump", "rabbitmq-definitions", "redis-rdb")
MAX_TEXT_LENGTH = 256
MAX_METADATA_ITEMS = 16


def _text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    if len(normalized) > MAX_TEXT_LENGTH:
        raise ValueError(f"{name} exceeds {MAX_TEXT_LENGTH} characters")
    return normalized


def _metadata(values: Metadata) -> Metadata:
    if len(values) > MAX_METADATA_ITEMS:
        raise ValueError(f"metadata exceeds {MAX_METADATA_ITEMS} items")
    normalized = tuple(sorted((_text(key, "metadata key"), _text(value, "metadata value")) for key, value in values))
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("metadata keys must be unique")
    return normalized


def _digest(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class RecoveryArtifact:
    artifact_id: str
    service: RecoveryService
    format: RecoveryFormat
    source_revision: str
    relative_path: str
    sha256: str
    byte_size: int
    restore_order: int
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.artifact_id, "artifact_id"),
            (self.source_revision, "source_revision"),
            (self.relative_path, "relative_path"),
        ):
            object.__setattr__(self, name, _text(value, name))
        if self.service not in SERVICES:
            raise ValueError("unknown recovery service")
        if self.format not in FORMATS:
            raise ValueError("unknown recovery format")
        if len(self.sha256) != 64 or any(character not in "0123456789abcdef" for character in self.sha256):
            raise ValueError("sha256 must be a lowercase SHA-256 digest")
        if self.byte_size < 0:
            raise ValueError("byte_size must be non-negative")
        if self.restore_order <= 0:
            raise ValueError("restore_order must be positive")
        path = PurePosixPath(self.relative_path.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
            raise ValueError("relative_path must remain inside the package")
        if str(path) != self.relative_path.replace("\\", "/"):
            raise ValueError("relative_path must be normalized")
        object.__setattr__(self, "relative_path", path.as_posix())
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def payload(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "service": self.service,
            "format": self.format,
            "source_revision": self.source_revision,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "restore_order": self.restore_order,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class RecoveryPackage:
    package_id: str
    created_at: str
    source_revision: str
    artifacts: tuple[RecoveryArtifact, ...]
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.package_id, "package_id"),
            (self.created_at, "created_at"),
            (self.source_revision, "source_revision"),
        ):
            object.__setattr__(self, name, _text(value, name))
        if len(self.artifacts) != len(SERVICES):
            raise ValueError("recovery package services must contain one artifact per service")
        if {artifact.service for artifact in self.artifacts} != set(SERVICES):
            raise ValueError("recovery package services must be unique and complete")
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("recovery artifact identifiers must be unique")
        orders = [artifact.restore_order for artifact in self.artifacts]
        if sorted(orders) != list(range(1, len(SERVICES) + 1)):
            raise ValueError("restore_order must be contiguous starting at 1")
        if any(artifact.source_revision != self.source_revision for artifact in self.artifacts):
            raise ValueError("artifact revisions must match package source_revision")
        object.__setattr__(self, "artifacts", tuple(sorted(self.artifacts, key=lambda item: item.restore_order)))
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def payload(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "created_at": self.created_at,
            "source_revision": self.source_revision,
            "artifacts": [artifact.payload() for artifact in self.artifacts],
            "metadata": self.metadata,
        }

    @property
    def digest(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True, slots=True)
class RecoveryRehearsal:
    status: Literal["ready", "blocked"]
    reasons: tuple[str, ...]
    package_digest: str
    verified_artifacts: int

    def __post_init__(self) -> None:
        if self.status not in ("ready", "blocked"):
            raise ValueError("unknown rehearsal status")
        if (self.status == "ready") == bool(self.reasons):
            raise ValueError("ready requires no reasons and blocked requires reasons")
        if len(self.package_digest) != 64:
            raise ValueError("package_digest must be a SHA-256 digest")
        if self.verified_artifacts < 0:
            raise ValueError("verified_artifacts must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reasons": self.reasons,
            "package_digest": self.package_digest,
            "verified_artifacts": self.verified_artifacts,
        }


def rehearse(package: RecoveryPackage, package_root: Path) -> RecoveryRehearsal:
    reasons: list[str] = []
    verified = 0
    root = package_root.resolve()
    for artifact in package.artifacts:
        target = (root / Path(artifact.relative_path)).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            reasons.append(f"unsafe_path:{artifact.service}")
            continue
        if not target.is_file():
            reasons.append(f"missing_payload:{artifact.service}")
            continue
        actual_size = target.stat().st_size
        if actual_size != artifact.byte_size:
            reasons.append(f"size_mismatch:{artifact.service}")
            continue
        if sha256_file(target) != artifact.sha256:
            reasons.append(f"checksum_mismatch:{artifact.service}")
            continue
        verified += 1
    status: Literal["ready", "blocked"] = "blocked" if reasons else "ready"
    return RecoveryRehearsal(status, tuple(reasons), package.digest, verified)


@dataclass(frozen=True, slots=True)
class RollbackManifest:
    manifest_id: str
    target_revision: str
    package_digest: str
    operator: str
    intent: str
    confirmation: Metadata

    def __post_init__(self) -> None:
        for value, name in (
            (self.manifest_id, "manifest_id"),
            (self.target_revision, "target_revision"),
            (self.operator, "operator"),
            (self.intent, "intent"),
        ):
            object.__setattr__(self, name, _text(value, name))
        if len(self.package_digest) != 64:
            raise ValueError("package_digest must be a SHA-256 digest")
        object.__setattr__(self, "confirmation", _metadata(self.confirmation))
        if not any(key == "ack" and value == "required" for key, value in self.confirmation):
            raise ValueError("rollback confirmation must include ack=required")

    def payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "target_revision": self.target_revision,
            "package_digest": self.package_digest,
            "operator": self.operator,
            "intent": self.intent,
            "confirmation": self.confirmation,
        }

    @property
    def digest(self) -> str:
        return _digest(self.payload())
