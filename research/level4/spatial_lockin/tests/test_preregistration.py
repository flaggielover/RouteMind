from __future__ import annotations

import unittest
from pathlib import Path
from typing import cast

from research.level4.spatial_lockin.preregistration import Preregistration
from research.level4.spatial_lockin.run import verify_preregistration

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class PreregistrationTests(unittest.TestCase):
    def test_frozen_digest_matches_manifest(self) -> None:
        preregistration = Preregistration.load(
            PACKAGE_ROOT / "configs" / "preregistration.json"
        )
        expected = (
            (PACKAGE_ROOT / "configs" / "preregistration.sha256")
            .read_text(encoding="ascii")
            .split()[0]
        )
        self.assertEqual(preregistration.digest, expected)
        self.assertEqual(verify_preregistration()["status"], "PASS")

    def test_seed_and_nonlinearity_families_are_frozen(self) -> None:
        payload = Preregistration.load(
            PACKAGE_ROOT / "configs" / "preregistration.json"
        ).payload
        identification = cast(dict[str, object], payload["identification"])
        validation = cast(dict[str, object], payload["validation"])
        self.assertEqual(identification["seeds"], list(range(11000, 11064)))
        self.assertEqual(validation["seeds"], list(range(21000, 21064)))
        self.assertEqual(
            payload["nonlinearities"], ["tanh", "logistic", "clipped_linear", "atan"]
        )


if __name__ == "__main__":
    unittest.main()
