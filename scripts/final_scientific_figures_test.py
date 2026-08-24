from __future__ import annotations

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from final_scientific_figures import (
    PLAN_PATH,
    ROOT,
    FinalFiguresError,
    _json,
    _verify_repository_sources,
    _write_once,
    build_support_rows,
    extract_claim_rows,
    validate_committed,
    validate_plan,
)


class FinalScientificFiguresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = _json(PLAN_PATH)
        cls.sources = _verify_repository_sources(cls.plan, ROOT)

    def test_live_plan_prohibits_experiment_execution_and_tuning(self) -> None:
        validate_plan(self.plan)

        self.assertEqual(
            self.plan["execution_policy"],
            {
                "run_experiments": False,
                "rerun_r3_325": False,
                "tune_or_reinterpret": False,
                "synthetic_fill": False,
                "drop_negative_outcomes": False,
            },
        )

    def test_live_support_rows_retain_no_data_and_unsupported_states(self) -> None:
        rows = build_support_rows(
            self.sources["twin_manifest"],
            self.sources["rads_manifest"],
            self.sources["independent_reproduction"],
        )

        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row["exclusion_status"].startswith("NONE_") for row in rows))
        self.assertEqual(sum(row["observed"] == 0 for row in rows), 5)
        self.assertEqual(
            sum(row["status"] == "UNSUPPORTED_REGIME_NOT_PRESENT" for row in rows),
            1,
        )

    def test_live_claim_rows_have_zero_supported_claims(self) -> None:
        rows = extract_claim_rows(self.sources["claim_matrix"])

        self.assertEqual(len(rows), 7)
        self.assertEqual(sum(row["supported_claim"] == "YES" for row in rows), 0)
        self.assertEqual(sum(row["final_status"] == "C-NO-NOVELTY" for row in rows), 2)
        self.assertEqual(sum(row["final_status"] == "C-NO-CLAIM" for row in rows), 5)

    def test_committed_bundle_is_complete_and_svg_files_are_parseable(self) -> None:
        result = validate_committed(PLAN_PATH, ROOT)

        self.assertEqual(result["artifact_count"], 6)
        self.assertEqual(result["negative_outcomes"]["c_pass_claims"], 0)
        self.assertEqual(result["negative_outcomes"]["excluded_rows"], 0)
        output_root = ROOT / self.plan["output"]["repository_relative_root"]
        for figure in self.plan["figures"]:
            root = ET.fromstring((output_root / figure["file"]).read_bytes())
            self.assertTrue(root.tag.endswith("svg"))
            self.assertGreater(len(list(root.iter())), 10)

    def test_external_write_once_is_idempotent_and_rejects_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.csv"
            _write_once(path, b"header\nvalue\n")
            _write_once(path, b"header\nvalue\n")

            self.assertEqual(
                path.with_name("artifact.csv.sha256").read_text(encoding="ascii").strip(),
                "2438de117fe81b671bd30d925d93f6883c660182dd44def976c1bdf63680022d",
            )
            with self.assertRaisesRegex(FinalFiguresError, "write-once artifact collision"):
                _write_once(path, b"changed\n")

    def test_plan_digest_tampering_is_rejected(self) -> None:
        mutated = json.loads(json.dumps(self.plan))
        mutated["execution_policy"]["rerun_r3_325"] = True

        with self.assertRaisesRegex(FinalFiguresError, "digest mismatch"):
            validate_plan(mutated)


if __name__ == "__main__":
    unittest.main()
