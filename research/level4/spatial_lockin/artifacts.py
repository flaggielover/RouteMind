from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .preregistration import canonical_json, payload_digest
from .reason_codes import fail

ArtifactClass = Literal["confirmatory", "diagnostic"]


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    artifact_class: ArtifactClass
    relative_path: str
    path: Path
    sha256: str
    content_digest: str


class ArtifactStore:
    def __init__(self, data_root: Path) -> None:
        root = data_root.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            fail("ARTIFACT_ROOT_MISSING", str(root))
        self.root = root / "research" / "level4" / "spatial_lockin"

    @classmethod
    def from_environment(cls, variable: str = "ROUTEMIND_DATA_ROOT") -> ArtifactStore:
        configured = os.environ.get(variable, "").strip()
        if not configured:
            fail("ARTIFACT_ROOT_MISSING", variable)
        return cls(Path(configured))

    def class_root(self, artifact_class: ArtifactClass) -> Path:
        if artifact_class not in ("confirmatory", "diagnostic"):
            fail("ARTIFACT_CLASS_MISMATCH", str(artifact_class))
        return (self.root / artifact_class).resolve()

    def resolve(self, artifact_class: ArtifactClass, relative_path: str) -> Path:
        if not relative_path or "\\" in relative_path:
            fail("ARTIFACT_PATH_UNSAFE", relative_path)
        relative = Path(relative_path)
        if relative.is_absolute() or any(part in ("", "..") for part in relative.parts):
            fail("ARTIFACT_PATH_UNSAFE", relative_path)
        class_root = self.class_root(artifact_class)
        target = (class_root / relative).resolve()
        try:
            target.relative_to(class_root)
        except ValueError:
            fail("ARTIFACT_PATH_UNSAFE", relative_path)
        return target

    def write_json(
        self,
        artifact_class: ArtifactClass,
        relative_path: str,
        payload: dict[str, object],
    ) -> StoredArtifact:
        target = self.resolve(artifact_class, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content_digest = payload_digest(payload)
        envelope = {
            "artifact_class": artifact_class,
            "content_digest": content_digest,
            "payload": payload,
        }
        encoded = (canonical_json(envelope) + "\n").encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        sidecar = target.with_suffix(target.suffix + ".sha256")
        if target.exists() or sidecar.exists():
            fail("ARTIFACT_EXISTS", relative_path)
        try:
            with target.open("xb") as stream:
                stream.write(encoded)
            with sidecar.open("x", encoding="ascii", newline="\n") as stream:
                stream.write(f"{digest}  {target.name}\n")
        except FileExistsError:
            fail("ARTIFACT_EXISTS", relative_path)
        return StoredArtifact(
            artifact_class, relative_path, target, digest, content_digest
        )

    def read_json(
        self,
        artifact_class: ArtifactClass,
        relative_path: str,
        *,
        expected_sha256: str | None = None,
    ) -> tuple[dict[str, object], StoredArtifact]:
        target = self.resolve(artifact_class, relative_path)
        sidecar = target.with_suffix(target.suffix + ".sha256")
        if not target.is_file() or not sidecar.is_file():
            fail("STAGE_ORDER_VIOLATION", relative_path)
        encoded = target.read_bytes()
        digest = hashlib.sha256(encoded).hexdigest()
        sidecar_digest = sidecar.read_text(encoding="ascii").split(maxsplit=1)[0]
        if digest != sidecar_digest or (
            expected_sha256 is not None and digest != expected_sha256
        ):
            fail("ARTIFACT_DIGEST_MISMATCH", relative_path)
        try:
            envelope = json.loads(encoded)
        except json.JSONDecodeError as exc:
            fail("ARTIFACT_DIGEST_MISMATCH", str(exc))
        if (
            not isinstance(envelope, dict)
            or envelope.get("artifact_class") != artifact_class
        ):
            fail("ARTIFACT_CLASS_MISMATCH", relative_path)
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            fail("ARTIFACT_DIGEST_MISMATCH", "payload is not an object")
        content_digest = payload_digest(payload)
        if content_digest != envelope.get("content_digest"):
            fail("ARTIFACT_DIGEST_MISMATCH", "content digest changed")
        return payload, StoredArtifact(
            artifact_class, relative_path, target, digest, content_digest
        )
