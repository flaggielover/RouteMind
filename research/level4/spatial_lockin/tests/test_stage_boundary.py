from __future__ import annotations

import unittest
from collections.abc import Iterable
from typing import cast

from research.level4.spatial_lockin.run import _parser


class StageBoundaryTests(unittest.TestCase):
    def test_withheld_validation_command_does_not_exist_before_threshold_push(
        self,
    ) -> None:
        parser = _parser()
        command_action = next(
            action for action in parser._actions if action.dest == "command"
        )
        self.assertIsNotNone(command_action.choices)
        choices = tuple(cast(Iterable[str], command_action.choices))
        self.assertNotIn("validate-threshold", choices)
        self.assertNotIn("validate-intervention", choices)
        self.assertIn("freeze-threshold", choices)
        self.assertIn("run-gate2", choices)
        self.assertIn("run-negative-control-diagnostic", choices)
        self.assertIn("verify-gate2b-preregistration", choices)
        self.assertIn("run-gate2b-calibration", choices)
        self.assertIn("run-gate2b-holdout", choices)
        self.assertIn("run-gate2b-coarse", choices)
        self.assertIn("run-gate2b-fine", choices)
        self.assertIn("finalize-gate2b", choices)
        self.assertNotIn("run-gate3", choices)


if __name__ == "__main__":
    unittest.main()
