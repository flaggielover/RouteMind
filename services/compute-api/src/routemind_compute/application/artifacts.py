from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_SHA256: Final = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_TYPES: Final = frozenset({"artifact", "dataset", "matrix", "road-graph", "replay"})


class ArtifactResolutionError(ValueError):
    """Raised when an external data artifact cannot be verified safely."""


@dataclass(frozen=True, slots=True)
class DataArtifactManifest:
    artifact_id: str
    artifact_type: str
    relative_path: str
    sha256: str
    producer: str
    revision: str
    configuration: tuple[tuple[str, str], ...]
    seed: int

    def __post_init__(self) -> None:
        for value, label in (
            (self.artifact_id, "artifact id"),
            (self.artifact_type, "artifact type"),
            (self.relative_path, "relative path"),
            (self.producer, "producer"),
            (self.revision, "revision"),
        ):
            if not value.strip():
                raise ValueError(f"{label} must not be blank")
        if self.artifact_type not in _ALLOWED_TYPES:
            raise ValueError("artifact type is not supported")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("artifact sha256 must be a lowercase SHA-256 digest")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("artifact seed must be an integer")
        if self.relative_path.startswith(("/", "\\")) or "\\" in self.relative_path:
            raise ValueError("artifact path must use a relative POSIX path")
        parts = self.relative_path.split("/")
        if any(not part or part == ".." for part in parts) or ":" in parts[0]:
            raise ValueError("artifact path must be safe and repository-relative")
        keys = [key for key, _ in self.configuration]
        if any(not key.strip() for key in keys):
            raise ValueError("artifact configuration keys must not be blank")
        if len(keys) != len(set(keys)):
            raise ValueError("artifact configuration keys must be unique")
        object.__setattr__(self, "configuration", tuple(sorted(self.configuration)))

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "producer": self.producer,
            "revision": self.revision,
            "configuration": list(self.configuration),
            "seed": self.seed,
        }

    def resolve(self, data_root: Path) -> Path:
        root = data_root.expanduser().resolve()
        target = (root / self.relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ArtifactResolutionError("artifact path escapes data root") from exc
        if target == root:
            raise ArtifactResolutionError("artifact path must identify a file below data root")
        return target


@dataclass(frozen=True, slots=True)
class ResolvedArtifact:
    manifest: DataArtifactManifest
    path: Path
    actual_sha256: str

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "artifact_id": self.manifest.artifact_id,
            "artifact_type": self.manifest.artifact_type,
            "path": self.manifest.relative_path,
            "sha256": self.actual_sha256,
            "producer": self.manifest.producer,
            "revision": self.manifest.revision,
            "manifest_digest": self.manifest.digest,
            "seed": self.manifest.seed,
        }


class DataRootArtifactAdapter:
    """Resolve and verify large external artifacts without copying them."""

    def __init__(self, data_root: Path) -> None:
        root = data_root.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ArtifactResolutionError("data root must exist and be a directory")
        self.data_root = root

    @classmethod
    def from_environment(cls, variable: str = "ROUTEMIND_DATA_ROOT") -> DataRootArtifactAdapter:
        configured = os.environ.get(variable, "").strip()
        if not configured:
            raise ArtifactResolutionError(f"{variable} is not configured")
        return cls(Path(configured))

    def resolve(self, manifest: DataArtifactManifest) -> ResolvedArtifact:
        path = manifest.resolve(self.data_root)
        if not path.exists() or not path.is_file():
            raise ArtifactResolutionError(f"artifact payload is missing: {manifest.artifact_id}")
        actual_sha256 = _sha256_file(path)
        if actual_sha256 != manifest.sha256:
            raise ArtifactResolutionError(f"artifact checksum mismatch: {manifest.artifact_id}")
        return ResolvedArtifact(manifest, path, actual_sha256)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as payload:
        for chunk in iter(lambda: payload.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
