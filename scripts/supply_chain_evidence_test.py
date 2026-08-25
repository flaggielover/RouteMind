from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import supply_chain_evidence as evidence


REVISION = "a" * 40


class SupplyChainEvidenceTests(unittest.TestCase):
    def test_builds_content_bound_sbom_and_provenance_with_resolved_containers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root)
            output = root / "output"
            summary = evidence.build_bundle(
                root,
                root / "java-tree.txt",
                root / "manifests",
                output,
                True,
                "2026-08-25T06:00:00Z",
                REVISION,
            )

            self.assertEqual(summary["ecosystemCounts"], {"maven": 1, "pypi": 1, "npm": 1, "oci": 1})
            self.assertFalse(summary["signed"])
            statement = json.loads((output / "routemind.provenance.intoto.json").read_text())
            self.assertEqual(statement["_type"], "https://in-toto.io/Statement/v1")
            self.assertEqual(statement["subject"][0]["digest"]["sha256"], summary["sbomSha256"])
            self.assertEqual(evidence.validate_bundle(output, 1)["sourceRevision"], REVISION)

    def test_missing_registry_manifest_fails_closed_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root)
            (root / "manifests/postgres.manifest.json").unlink()
            with self.assertRaisesRegex(ValueError, "registry manifest missing"):
                evidence.build_bundle(
                    root,
                    root / "java-tree.txt",
                    root / "manifests",
                    root / "output",
                    True,
                    "2026-08-25T06:00:00Z",
                    REVISION,
                )

    def test_digest_mutation_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root)
            output = root / "output"
            evidence.build_bundle(
                root,
                root / "java-tree.txt",
                root / "manifests",
                output,
                True,
                "2026-08-25T06:00:00Z",
                REVISION,
            )
            (output / "routemind.cdx.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "CycloneDX|component count|digest"):
                evidence.validate_bundle(output, 1)

    @staticmethod
    def _fixture(root: Path) -> None:
        (root / "services/compute-api").mkdir(parents=True)
        (root / "apps/web").mkdir(parents=True)
        (root / "manifests").mkdir()
        (root / "java-tree.txt").write_text(
            "org.example:library:jar:1.2.3:compile\n", encoding="utf-8"
        )
        (root / "services/compute-api/uv.lock").write_text(
            "version = 1\nrevision = 3\n[[package]]\nname = \"demo\"\nversion = \"2.0.0\"\n"
            "sdist = { hash = \"sha256:" + ("b" * 64) + "\" }\n",
            encoding="utf-8",
        )
        (root / "apps/web/package-lock.json").write_text(
            json.dumps(
                {
                    "lockfileVersion": 3,
                    "packages": {"node_modules/demo": {"version": "3.0.0", "integrity": "sha512-demo"}},
                }
            ),
            encoding="utf-8",
        )
        (root / "compose.yaml").write_text(
            "services:\n  postgres:\n    image: ${POSTGRES_IMAGE:-postgres:18.6-alpine}\n",
            encoding="utf-8",
        )
        (root / "manifests/postgres.manifest.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.oci.image.index.v1+json",
                    "manifests": [{"digest": "sha256:" + ("c" * 64)}],
                }
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
