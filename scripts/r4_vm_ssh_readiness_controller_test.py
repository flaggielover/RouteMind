from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "r4_vm_ssh_readiness_diagnostic.ps1"


class ControllerBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_exact_contract_and_resource_boundaries_are_frozen(self) -> None:
        for value in (
            "2ba069c9886c69f1b38a22740c6c2367bd21a2bd129e8ff6c8148f336a46fbb7",
            '"nrt"',
            '"vc2-1c-1gb"',
            '"22"',
            'imageId = 2284',
            'incrementalCeilingUsdCents = 100',
        ):
            self.assertIn(value, self.text)

    def test_mutation_is_double_gated_and_teardown_is_finally_guarded(self) -> None:
        self.assertIn("-AcknowledgeExternalExecution", self.text)
        self.assertIn("ROUTEMIND_VM_SSH_READINESS_V1_APPROVAL_DIGEST", self.text)
        finally_block = self.text.split("} finally {", 1)[1]
        self.assertIn("Invoke-Teardown", finally_block)
        self.assertIn('"--allow-partial-destroy"', self.text)

    def test_no_unsafe_ssh_or_broad_delete_shortcuts(self) -> None:
        for forbidden in (
            "StrictHostKeyChecking=accept-new",
            "StrictHostKeyChecking=no",
            "Remove-Item $DataRoot",
            "0.0.0.0/0",
            "::/0",
        ):
            self.assertNotIn(forbidden, self.text)

    def test_evidence_redacts_operator_and_scans_secret_values(self) -> None:
        self.assertIn("OPERATOR_IPV4_REDACTED", self.text)
        self.assertIn("leakage-scan.json", self.text)
        self.assertIn("secretFindings = $findings", self.text)
        self.assertIn("executionLabelResourceCount = 0", self.text)
        self.assertIn("NO_INDEPENDENT_HOST_KEY_SOURCE_AND_STRICT_AUTH_NOT_REACHED", self.text)
        self.assertIn("$diagnosticIncomplete = [bool]$failurePhase -or -not $guestEvidence", self.text)

    def test_get_only_finalizer_can_close_post_teardown_artifacts(self) -> None:
        self.assertIn('"Finalize" {', self.text)
        self.assertIn("GET-only cleanup re-verification failed", self.text)
        self.assertIn("artifactManifestComplete = $true", self.text)
        self.assertIn("if (-not (Test-Path -LiteralPath $costPath))", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
