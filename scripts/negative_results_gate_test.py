from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import negative_results_gate as gate


def _write_fixture(root: Path, ledger_text: str) -> Path:
    ledger = root / "docs/research/r3/NEGATIVE_RESULTS.md"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(ledger_text, encoding="utf-8")
    source = root / "evidence/source.md"
    source.parent.mkdir(parents=True)
    source.write_text("source evidence\n", encoding="utf-8")
    entries = gate.extract_entries(ledger_text)
    unsigned: dict[str, object] = {
        "schema_version": "routemind-negative-results-audit-v1",
        "task_id": "R3-358",
        "ledger_path": "docs/research/r3/NEGATIVE_RESULTS.md",
        "frozen_entry_count": 2,
        "ledger_prefix_digest": gate.prefix_digest(entries, 2),
        "required_task_coverage": ["R3-311", "R3-325"],
        "category_entries": {"failures": ["NR-R3-001", "NR-R3-002"]},
        "source_artifacts": [
            {
                "path": "evidence/source.md",
                "sha256": gate.hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        ],
    }
    manifest = {"manifest_digest": gate._canonical_digest(unsigned), **unsigned}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class NegativeResultsGateTests(unittest.TestCase):
    def test_repository_frozen_ledger_is_valid(self) -> None:
        result = gate.validate_negative_results()
        self.assertEqual(result["frozen_entry_count"], 31)
        self.assertEqual(result["total_entry_count"], 31)

    def test_future_append_preserves_frozen_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = (
                "# Ledger\n\n"
                "- `NR-R3-001`: R3-311 failed hypothesis.\n"
                "- `NR-R3-002`: R3-325 retained S-FAIL.\n"
            )
            manifest = _write_fixture(root, original)
            ledger = root / "docs/research/r3/NEGATIVE_RESULTS.md"
            ledger.write_text(
                original + "- `NR-R3-003`: R3-327 remains C-NO-CLAIM.\n",
                encoding="utf-8",
            )
            result = gate.validate_negative_results(root, manifest)
            self.assertEqual(result["frozen_entry_count"], 2)
            self.assertEqual(result["total_entry_count"], 3)

    def test_mutation_or_deletion_of_frozen_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = (
                "- `NR-R3-001`: R3-311 failed hypothesis.\n"
                "- `NR-R3-002`: R3-325 retained S-FAIL.\n"
            )
            manifest = _write_fixture(root, original)
            ledger = root / "docs/research/r3/NEGATIVE_RESULTS.md"
            ledger.write_text(original.replace("S-FAIL", "S-PASS"), encoding="utf-8")
            with self.assertRaisesRegex(gate.NegativeResultsGateError, "modified"):
                gate.validate_negative_results(root, manifest)
            ledger.write_text(original.splitlines(keepends=True)[0], encoding="utf-8")
            with self.assertRaisesRegex(gate.NegativeResultsGateError, "deleted"):
                gate.validate_negative_results(root, manifest)


if __name__ == "__main__":
    unittest.main()
