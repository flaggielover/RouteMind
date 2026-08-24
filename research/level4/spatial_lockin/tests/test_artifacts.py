from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.level4.spatial_lockin.artifacts import ArtifactStore
from research.level4.spatial_lockin.reason_codes import ResearchGateError


class ArtifactTests(unittest.TestCase):
    def test_class_roots_are_disjoint_and_artifacts_are_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory))
            artifact = store.write_json(
                "confirmatory", "stage/result.json", {"value": 1}
            )
            self.assertNotEqual(
                store.class_root("confirmatory"), store.class_root("diagnostic")
            )
            payload, verified = store.read_json(
                "confirmatory", "stage/result.json", expected_sha256=artifact.sha256
            )
            self.assertEqual(payload, {"value": 1})
            self.assertEqual(verified.sha256, artifact.sha256)
            with self.assertRaisesRegex(ResearchGateError, "ARTIFACT_EXISTS"):
                store.write_json("confirmatory", "stage/result.json", {"value": 2})
            with self.assertRaisesRegex(ResearchGateError, "STAGE_ORDER_VIOLATION"):
                store.read_json("diagnostic", "stage/result.json")

    def test_digest_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory))
            artifact = store.write_json(
                "confirmatory", "stage/result.json", {"value": 1}
            )
            artifact.path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ResearchGateError, "ARTIFACT_DIGEST_MISMATCH"):
                store.read_json("confirmatory", "stage/result.json")

    def test_unsafe_relative_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory))
            with self.assertRaisesRegex(ResearchGateError, "ARTIFACT_PATH_UNSAFE"):
                store.resolve("confirmatory", "../diagnostic/result.json")


if __name__ == "__main__":
    unittest.main()
