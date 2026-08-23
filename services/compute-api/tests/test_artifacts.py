from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from routemind_compute.application.artifacts import (
    ArtifactResolutionError,
    DataArtifactManifest,
    DataRootArtifactAdapter,
)


def manifest_for(
    relative_path: str = "maps/network.json", **overrides: object
) -> DataArtifactManifest:
    values: dict[str, object] = {
        "artifact_id": "network-1",
        "artifact_type": "road-graph",
        "relative_path": relative_path,
        "sha256": "0" * 64,
        "producer": "fixture-builder",
        "revision": "git:abc123",
        "configuration": (("speed", "30"), ("zone", "north")),
        "seed": 7,
    }
    values.update(overrides)
    return DataArtifactManifest(**values)  # type: ignore[arg-type]


def test_data_root_adapter_resolves_and_verifies_external_artifacts(tmp_path: Path) -> None:
    payload = b"network fixture\n"
    artifact_path = tmp_path / "maps" / "network.json"
    artifact_path.parent.mkdir()
    artifact_path.write_bytes(payload)
    manifest = manifest_for(sha256=hashlib.sha256(payload).hexdigest())

    resolved = DataRootArtifactAdapter(tmp_path).resolve(manifest)

    assert resolved.path == artifact_path.resolve()
    assert resolved.actual_sha256 == manifest.sha256
    assert resolved.metadata["manifest_digest"] == manifest.digest
    assert resolved.metadata["reference_data_id"] == "road-graph:network-1:git:abc123"


def test_manifest_digest_canonicalizes_configuration() -> None:
    first = manifest_for(configuration=(("zone", "north"), ("speed", "30")))
    second = manifest_for(configuration=(("speed", "30"), ("zone", "north")))

    assert first.configuration == (("speed", "30"), ("zone", "north"))
    assert first.digest == second.digest


def test_adapter_rejects_missing_and_corrupt_payloads(tmp_path: Path) -> None:
    adapter = DataRootArtifactAdapter(tmp_path)
    with pytest.raises(ArtifactResolutionError, match="missing"):
        adapter.resolve(manifest_for())

    payload = tmp_path / "maps" / "network.json"
    payload.parent.mkdir()
    payload.write_bytes(b"changed")
    with pytest.raises(ArtifactResolutionError, match="checksum"):
        adapter.resolve(manifest_for())


def test_manifest_rejects_unsafe_paths_and_invalid_metadata(tmp_path: Path) -> None:
    invalid_values = (
        {"relative_path": "../outside"},
        {"relative_path": "C:/outside"},
        {"relative_path": "maps\\outside"},
        {"sha256": "not-a-digest"},
        {"artifact_type": "unknown"},
        {"configuration": (("speed", "30"), ("speed", "31"))},
        {"seed": True},
    )
    for overrides in invalid_values:
        with pytest.raises(ValueError):
            manifest_for(**overrides)

    with pytest.raises(ArtifactResolutionError, match="directory"):
        DataRootArtifactAdapter(tmp_path / "missing")


def test_environment_adapter_requires_a_configured_existing_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ROUTEMIND_DATA_ROOT", raising=False)
    with pytest.raises(ArtifactResolutionError, match="not configured"):
        DataRootArtifactAdapter.from_environment()
    monkeypatch.setenv("ROUTEMIND_DATA_ROOT", str(tmp_path))
    assert DataRootArtifactAdapter.from_environment().data_root == tmp_path.resolve()
