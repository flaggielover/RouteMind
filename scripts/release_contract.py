from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

Metadata = tuple[tuple[str, str], ...]
ReleaseService = Literal["business-api", "compute-api", "web"]

SERVICES: tuple[ReleaseService, ...] = ("business-api", "compute-api", "web")
DEFAULT_REQUIRED_FILES = ("compose.yaml", "TASK_GRAPH.yaml", "scripts/verify.ps1")
_SEMVER = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_MUTABLE_VERSIONS = {"latest", "stable", "current", "main", "master"}


def _text(value: str) -> str:
    return value.strip()


def _metadata(values: Metadata) -> Metadata:
    return tuple(sorted((_text(key), _text(value)) for key, value in values))


def _digest(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _valid_immutable_version(value: str) -> bool:
    return bool(_SEMVER.fullmatch(value) or _DIGEST.fullmatch(value))


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    service: str
    version_or_digest: str
    source_revision: str
    provenance: Metadata
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "service", _text(self.service))
        object.__setattr__(self, "version_or_digest", _text(self.version_or_digest))
        object.__setattr__(self, "source_revision", _text(self.source_revision))
        object.__setattr__(self, "provenance", _metadata(self.provenance))
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def payload(self) -> dict[str, object]:
        return {
            "service": self.service,
            "version_or_digest": self.version_or_digest,
            "source_revision": self.source_revision,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    release_id: str
    source_revision: str
    created_at: str
    environment: str
    artifacts: tuple[ArtifactDescriptor, ...]
    contract_versions: Metadata
    migration_heads: tuple[str, ...]
    health_checks: Metadata
    rollback_package_digest: str
    metadata: Metadata = ()

    def __post_init__(self) -> None:
        for name in ("release_id", "source_revision", "created_at", "environment", "rollback_package_digest"):
            object.__setattr__(self, name, _text(getattr(self, name)))
        object.__setattr__(self, "artifacts", tuple(sorted(self.artifacts, key=lambda artifact: artifact.service)))
        object.__setattr__(self, "contract_versions", _metadata(self.contract_versions))
        object.__setattr__(self, "migration_heads", tuple(_text(head) for head in self.migration_heads))
        object.__setattr__(self, "health_checks", _metadata(self.health_checks))
        object.__setattr__(self, "metadata", _metadata(self.metadata))

    def payload(self) -> dict[str, object]:
        return {
            "release_id": self.release_id,
            "source_revision": self.source_revision,
            "created_at": self.created_at,
            "environment": self.environment,
            "artifacts": [artifact.payload() for artifact in self.artifacts],
            "contract_versions": self.contract_versions,
            "migration_heads": self.migration_heads,
            "health_checks": self.health_checks,
            "rollback_package_digest": self.rollback_package_digest,
            "metadata": self.metadata,
        }

    @property
    def digest(self) -> str:
        return _digest(self.payload())


@dataclass(frozen=True, slots=True)
class ReleasePreflight:
    status: Literal["ready", "blocked"]
    reasons: tuple[str, ...]
    manifest_digest: str
    verified_files: int

    def __post_init__(self) -> None:
        if self.status not in ("ready", "blocked"):
            raise ValueError("unknown preflight status")
        if (self.status == "ready") == bool(self.reasons):
            raise ValueError("ready requires no reasons and blocked requires reasons")
        if not re.fullmatch(r"[0-9a-f]{64}", self.manifest_digest):
            raise ValueError("manifest_digest must be a lowercase SHA-256 digest")
        if self.verified_files < 0:
            raise ValueError("verified_files must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reasons": self.reasons,
            "manifest_digest": self.manifest_digest,
            "verified_files": self.verified_files,
        }


def _duplicate_reasons(values: Metadata, prefix: str) -> list[str]:
    counts: dict[str, int] = {}
    for key, _ in values:
        counts[key] = counts.get(key, 0) + 1
    return [f"duplicate_{prefix}:{key}" for key in sorted(key for key, count in counts.items() if count > 1)]


def _manifest_reasons(manifest: ReleaseManifest) -> list[str]:
    reasons: list[str] = []
    required_text = {
        "release_id": manifest.release_id,
        "source_revision": manifest.source_revision,
        "created_at": manifest.created_at,
        "environment": manifest.environment,
    }
    reasons.extend(f"missing:{name}" for name, value in required_text.items() if not value)

    if not manifest.artifacts:
        reasons.append("artifacts:missing")
    artifact_services: list[str] = []
    for artifact in manifest.artifacts:
        service = artifact.service
        artifact_services.append(service)
        if service not in SERVICES:
            reasons.append(f"artifact_service:unknown:{service or '<blank>'}")
        if not artifact.version_or_digest:
            reasons.append(f"artifact_version:missing:{service or '<blank>'}")
        elif artifact.version_or_digest.lower() in _MUTABLE_VERSIONS:
            reasons.append(f"artifact_version:mutable:{service or '<blank>'}")
        elif not _valid_immutable_version(artifact.version_or_digest):
            reasons.append(f"artifact_version:not_immutable:{service or '<blank>'}")
        if not artifact.source_revision:
            reasons.append(f"artifact_revision:missing:{service or '<blank>'}")
        elif artifact.source_revision != manifest.source_revision:
            reasons.append(f"artifact_revision:mismatch:{service or '<blank>'}")
        if not artifact.provenance:
            reasons.append(f"artifact_provenance:missing:{service or '<blank>'}")
    reasons.extend(f"duplicate_artifact_service:{service}" for service in sorted(set(artifact_services)) if artifact_services.count(service) > 1)
    reasons.extend(f"missing_artifact_service:{service}" for service in SERVICES if service not in artifact_services)

    if not manifest.contract_versions:
        reasons.append("contracts:missing")
    reasons.extend(_duplicate_reasons(manifest.contract_versions, "contract"))
    reasons.extend(
        f"contract:incomplete:{key or '<blank>'}"
        for key, value in manifest.contract_versions
        if not key or not value
    )

    if not manifest.migration_heads:
        reasons.append("migrations:missing")
    reasons.extend(
        f"migration_head:missing:{index}"
        for index, head in enumerate(manifest.migration_heads)
        if not head
    )
    reasons.extend(
        f"duplicate_migration_head:{head}"
        for head in sorted({head for head in manifest.migration_heads if head})
        if manifest.migration_heads.count(head) > 1
    )

    if not manifest.health_checks:
        reasons.append("health_checks:missing")
    reasons.extend(_duplicate_reasons(manifest.health_checks, "health_check"))
    health_services = {key for key, _ in manifest.health_checks}
    reasons.extend(
        f"health_check:incomplete:{key or '<blank>'}"
        for key, value in manifest.health_checks
        if not key or not value
    )
    reasons.extend(f"missing_health_check:{service}" for service in SERVICES if service not in health_services)
    reasons.extend(f"unknown_health_service:{service}" for service in sorted(health_services - set(SERVICES)))

    rollback = manifest.rollback_package_digest
    if not rollback:
        reasons.append("rollback_digest:missing")
    elif not re.fullmatch(r"[0-9a-f]{64}", rollback):
        reasons.append("rollback_digest:not_content_digest")
    return reasons


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return not path.is_absolute() and path != PurePosixPath(".") and ".." not in path.parts and str(path) == value.replace("\\", "/")


def preflight(
    manifest: ReleaseManifest,
    repo_root: Path,
    required_files: tuple[str, ...] = DEFAULT_REQUIRED_FILES,
) -> ReleasePreflight:
    reasons = _manifest_reasons(manifest)
    root = repo_root.resolve()
    verified_files = 0
    for relative in sorted(set(required_files)):
        if not _safe_relative_path(relative):
            reasons.append(f"required_file:unsafe_path:{relative}")
            continue
        target = (root / Path(relative)).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            reasons.append(f"required_file:unsafe_path:{relative}")
            continue
        if target.is_file():
            verified_files += 1
        else:
            reasons.append(f"required_file:missing:{relative}")
    stable_reasons = tuple(sorted(set(reasons)))
    status: Literal["ready", "blocked"] = "blocked" if stable_reasons else "ready"
    return ReleasePreflight(status, stable_reasons, manifest.digest, verified_files)
