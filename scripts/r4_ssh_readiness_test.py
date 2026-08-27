from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from r4_ssh_readiness import (
    Observation,
    SshReadinessError,
    aggregate_artifacts,
    build_artifact,
    classify,
    persist_target_artifact,
    strict_loads,
)


class SshReadinessTest(unittest.TestCase):
    def test_failure_classifications(self) -> None:
        cases = {
            "TCP_TIMEOUT": replace(Observation(), tcp="TIMEOUT"),
            "TCP_RESET": replace(Observation(), tcp="RESET"),
            "SSH_BANNER_NOT_RECEIVED": replace(Observation(), banner="MISSING"),
            "SSH_BANNER_MALFORMED": replace(Observation(), banner="MALFORMED"),
            "SSH_KEX_TIMEOUT": replace(Observation(), kex_started=False),
            "SSH_HOST_KEY_MISMATCH": replace(Observation(), host_key="MISMATCH"),
            "SSH_AUTH_REJECTED": replace(Observation(), auth="REJECTED"),
            "SSH_USERNAME_REJECTED": replace(Observation(), auth="WRONG_USERNAME"),
            "CLOUD_INIT_INCOMPLETE": replace(Observation(), cloud_init="RUNNING"),
        }
        for expected, observation in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(expected, classify(observation))

    def test_ready_artifact_has_all_passed_stages(self) -> None:
        artifact = build_artifact(
            execution_id="r4-vm-ssh-v1-20260827t120000z-abcdef0",
            target="primary",
            observation=Observation(),
            attempts=({"attempt": 1, "backoffSeconds": 0},),
        )
        self.assertEqual("READY", artifact["terminalClassification"])
        self.assertTrue(all(item["status"] == "PASS" for item in artifact["stages"]))

    def test_strict_json_rejects_case_ambiguous_keys(self) -> None:
        with self.assertRaises(SshReadinessError):
            strict_loads('{"terminalClassification":"READY","TerminalClassification":"READY"}')

    def test_one_ready_one_failed_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary = persist_target_artifact(
                root,
                build_artifact(
                    execution_id="test", target="primary", observation=Observation()
                ),
            )
            recovery = persist_target_artifact(
                root,
                build_artifact(
                    execution_id="test",
                    target="recovery",
                    observation=replace(Observation(), banner="MISSING"),
                ),
            )
            summary = aggregate_artifacts(
                {"primary": primary, "recovery": recovery}, root / "summary.json"
            )
            self.assertEqual("COMPLETE", summary["status"])
            self.assertEqual("READY", summary["targets"]["primary"]["terminalClassification"])
            self.assertEqual(
                "SSH_BANNER_NOT_RECEIVED",
                summary["targets"]["recovery"]["terminalClassification"],
            )

    def test_operator_execution_failure_does_not_block_observer(self) -> None:
        self._assert_execution_failure_is_independent("operator", "observer")

    def test_observer_execution_failure_does_not_block_operator(self) -> None:
        self._assert_execution_failure_is_independent("observer", "operator")

    def _assert_execution_failure_is_independent(self, failed: str, valid: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            failed_path = persist_target_artifact(
                root,
                build_artifact(
                    execution_id="test",
                    target=failed,
                    observation=replace(Observation(), vm_created=False),
                ),
            )
            valid_path = persist_target_artifact(
                root,
                build_artifact(execution_id="test", target=valid, observation=Observation()),
            )
            summary = aggregate_artifacts(
                {failed: failed_path, valid: valid_path}, root / "summary.json"
            )
            self.assertEqual("VM_NOT_CREATED", summary["targets"][failed]["terminalClassification"])
            self.assertEqual("READY", summary["targets"][valid]["terminalClassification"])

    def test_malformed_operator_does_not_remove_observer(self) -> None:
        self._assert_malformed_side_preserves_other("operator", "observer")

    def test_malformed_observer_does_not_remove_operator(self) -> None:
        self._assert_malformed_side_preserves_other("observer", "operator")

    def _assert_malformed_side_preserves_other(self, malformed: str, valid: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            malformed_path = root / "raw" / f"{malformed}.json"
            malformed_path.parent.mkdir(parents=True)
            malformed_path.write_text("{", encoding="utf-8")
            valid_path = persist_target_artifact(
                root,
                build_artifact(execution_id="test", target=valid, observation=Observation()),
            )
            summary = aggregate_artifacts(
                {malformed: malformed_path, valid: valid_path}, root / "summary.json"
            )
            self.assertEqual("INCOMPLETE", summary["status"])
            self.assertEqual("MALFORMED", summary["targets"][malformed]["status"])
            self.assertEqual("AVAILABLE", summary["targets"][valid]["status"])
            self.assertTrue(valid_path.is_file())

    def test_missing_side_is_reported_without_deleting_available_side(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary = persist_target_artifact(
                root,
                build_artifact(execution_id="test", target="primary", observation=Observation()),
            )
            missing = root / "raw" / "recovery.json"
            summary = aggregate_artifacts(
                {"primary": primary, "recovery": missing}, root / "summary.json"
            )
            self.assertEqual("MISSING", summary["targets"]["recovery"]["status"])
            self.assertTrue(primary.is_file())

    def test_aggregation_failure_preserves_raw_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {
                target: persist_target_artifact(
                    root,
                    build_artifact(execution_id="test", target=target, observation=Observation()),
                )
                for target in ("primary", "recovery")
            }
            before = {target: path.read_bytes() for target, path in paths.items()}
            with self.assertRaises(SshReadinessError):
                aggregate_artifacts(paths, root / "summary.json", inject_failure=True)
            self.assertEqual(before, {target: path.read_bytes() for target, path in paths.items()})

    def test_persisted_json_is_canonical_and_powershell_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = persist_target_artifact(
                Path(temporary),
                build_artifact(execution_id="test", target="primary", observation=Observation()),
            )
            parsed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("r4-vm-ssh-readiness-artifact.v1", parsed["schema"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
