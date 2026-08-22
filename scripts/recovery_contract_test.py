from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from recovery_contract import RecoveryArtifact, RecoveryPackage, RollbackManifest, rehearse


def package(root: Path) -> RecoveryPackage:
    definitions = {
        "postgres": ("pg_dump", "postgres.dump", b"postgres-fixture", 1),
        "rabbitmq": ("rabbitmq-definitions", "rabbitmq.json", b"rabbitmq-fixture", 2),
        "redis": ("redis-rdb", "redis.rdb", b"redis-fixture", 3),
    }
    artifacts: list[RecoveryArtifact] = []
    for service, (format_name, filename, content, order) in definitions.items():
        (root / filename).write_bytes(content)
        artifacts.append(
            RecoveryArtifact(
                f"artifact-{service}",
                service,  # type: ignore[arg-type]
                format_name,  # type: ignore[arg-type]
                "git:fixture",
                filename,
                hashlib.sha256(content).hexdigest(),
                len(content),
                order,
            )
        )
    return RecoveryPackage("package-1", "2026-08-22T14:00:00Z", "git:fixture", tuple(artifacts))


class RecoveryContractTests(unittest.TestCase):
    def test_rehearsal_verifies_checksum_size_and_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = package(root)
            result = rehearse(value, root)
            self.assertEqual(result.status, "ready")
            self.assertEqual(result.reasons, ())
            self.assertEqual(result.verified_artifacts, 3)
            self.assertEqual(result.package_digest, value.digest)
            self.assertEqual(value, RecoveryPackage(value.package_id, value.created_at, value.source_revision, tuple(reversed(value.artifacts))))

    def test_rehearsal_blocks_missing_size_and_checksum_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = package(root)
            (root / "rabbitmq.json").write_bytes(b"rabbitmq-mutated")
            (root / "redis.rdb").unlink()
            result = rehearse(value, root)
            self.assertEqual(result.status, "blocked")
            self.assertEqual(
                result.reasons,
                ("checksum_mismatch:rabbitmq", "missing_payload:redis"),
            )

    def test_package_rejects_incomplete_unsafe_or_inconsistent_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = package(root)
            with self.assertRaisesRegex(ValueError, "services"):
                RecoveryPackage(value.package_id, value.created_at, value.source_revision, value.artifacts[:2])
            with self.assertRaisesRegex(ValueError, "relative_path"):
                RecoveryArtifact("bad", "postgres", "pg_dump", "git:fixture", "../escape", "a" * 64, 1, 1)
            with self.assertRaisesRegex(ValueError, "contiguous"):
                RecoveryPackage(
                    value.package_id,
                    value.created_at,
                    value.source_revision,
                    tuple(
                        artifact if artifact.service != "redis" else RecoveryArtifact(
                            artifact.artifact_id,
                            artifact.service,
                            artifact.format,
                            artifact.source_revision,
                            artifact.relative_path,
                            artifact.sha256,
                            artifact.byte_size,
                            4,
                        )
                        for artifact in value.artifacts
                    ),
                )
            with self.assertRaisesRegex(ValueError, "revision"):
                RecoveryPackage(
                    value.package_id,
                    value.created_at,
                    "git:other",
                    value.artifacts,
                )

    def test_rollback_manifest_is_reproducible_and_requires_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = package(Path(directory))
        first = RollbackManifest(
            "rollback-1", "git:fixture", value.digest, "operator-1", "restore previous release", (("ack", "required"),)
        )
        second = RollbackManifest(
            "rollback-1", "git:fixture", value.digest, "operator-1", "restore previous release", (("ack", "required"),)
        )
        self.assertEqual(first.digest, second.digest)
        with self.assertRaisesRegex(ValueError, "ack=required"):
            RollbackManifest("rollback-2", "git:fixture", value.digest, "operator-1", "restore", ())
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            RollbackManifest("rollback-3", "git:fixture", "short", "operator-1", "restore", (("ack", "required"),))


if __name__ == "__main__":
    unittest.main()
