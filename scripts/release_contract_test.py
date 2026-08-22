from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from release_contract import ArtifactDescriptor, ReleaseManifest, preflight


def manifest(**overrides: object) -> ReleaseManifest:
    revision = "git:fixture"
    artifacts = tuple(
        ArtifactDescriptor(service, "1.2.3", revision, (("builder", "local"),))
        for service in ("business-api", "compute-api", "web")
    )
    values: dict[str, object] = {
        "release_id": "release-1",
        "source_revision": revision,
        "created_at": "2026-08-22T14:00:00Z",
        "environment": "staging",
        "artifacts": artifacts,
        "contract_versions": (("dispatch", "v1"), ("orders", "v1")),
        "migration_heads": ("V1", "V6"),
        "health_checks": (
            ("business-api", "business-api/health"),
            ("compute-api", "compute-api/health"),
            ("web", "web/smoke"),
        ),
        "rollback_package_digest": "a" * 64,
    }
    values.update(overrides)
    return ReleaseManifest(**values)  # type: ignore[arg-type]


class ReleaseContractTests(unittest.TestCase):
    def test_valid_preflight_is_ready_and_digest_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("compose.yaml", "TASK_GRAPH.yaml", "scripts/verify.ps1"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("fixture", encoding="utf-8")
            value = manifest()
            result = preflight(value, root)
            reordered = manifest(
                artifacts=tuple(reversed(value.artifacts)),
                contract_versions=tuple(reversed(value.contract_versions)),
                health_checks=tuple(reversed(value.health_checks)),
            )
            self.assertEqual(result.status, "ready")
            self.assertEqual(result.reasons, ())
            self.assertEqual(result.verified_files, 3)
            self.assertEqual(result.manifest_digest, value.digest)
            self.assertEqual(value.digest, reordered.digest)

    def test_mutable_and_incomplete_inputs_return_stable_blockers(self) -> None:
        value = manifest(
            artifacts=(ArtifactDescriptor("business-api", "latest", "git:other", ()),),
            contract_versions=(),
            migration_heads=("", "V1", "V1"),
            health_checks=(("business-api", ""),),
            rollback_package_digest="release-tag",
        )
        result = preflight(value, Path("."), ("missing.txt", "../escape"))
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.reasons, tuple(sorted(result.reasons)))
        self.assertIn("artifact_version:mutable:business-api", result.reasons)
        self.assertIn("artifact_provenance:missing:business-api", result.reasons)
        self.assertIn("rollback_digest:not_content_digest", result.reasons)
        self.assertIn("required_file:unsafe_path:../escape", result.reasons)
        self.assertIn("required_file:missing:missing.txt", result.reasons)

    def test_duplicate_services_contracts_and_health_are_blocked(self) -> None:
        value = manifest(
            artifacts=(
                ArtifactDescriptor("business-api", "1.2.3", "git:fixture", (("builder", "local"),)),
                ArtifactDescriptor("business-api", "1.2.4", "git:fixture", (("builder", "local"),)),
            ),
            contract_versions=(("orders", "v1"), ("orders", "v2")),
            health_checks=(("business-api", "health"), ("business-api", "health-2")),
        )
        result = preflight(value, Path("."), ())
        self.assertEqual(result.status, "blocked")
        self.assertIn("duplicate_artifact_service:business-api", result.reasons)
        self.assertIn("duplicate_contract:orders", result.reasons)
        self.assertIn("duplicate_health_check:business-api", result.reasons)
        self.assertIn("missing_artifact_service:compute-api", result.reasons)
        self.assertIn("missing_health_check:compute-api", result.reasons)

    def test_preflight_is_read_only_and_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            preflight(manifest(), root, ("../outside", "compose.yaml"))
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
