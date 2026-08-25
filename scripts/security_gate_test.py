from __future__ import annotations

import unittest
from pathlib import Path

import security_gate


class SecurityGateTests(unittest.TestCase):
    def test_repository_baseline_is_clean(self) -> None:
        self.assertEqual(security_gate.validate(), [])

    def test_high_confidence_material_is_detected(self) -> None:
        private_marker = "-----BEGIN " + "PRIVATE KEY-----"
        provider_token = "ghp_" + ("A" * 24)
        findings = security_gate.scan_text(
            Path("fixture.txt"),
            f"key={private_marker}\naccess_token={provider_token}\n",
        )
        self.assertGreaterEqual(len(findings), 2)
        self.assertTrue(any("private key material" in finding for finding in findings))
        self.assertTrue(any("high-confidence provider token" in finding for finding in findings))

    def test_local_placeholders_are_allowed(self) -> None:
        findings = security_gate.scan_text(
            Path("fixture.env"),
            "api_key=change-me-local-only\nsecret_key=${SECRET_KEY}\n",
        )
        self.assertEqual(findings, [])

    def test_supply_chain_automation_is_present(self) -> None:
        self.assertEqual(security_gate.check_supply_chain_automation(), [])

    def test_posix_wrapper_cannot_silently_open_instead_of_execute(self) -> None:
        findings = security_gate.check_maven_launcher_text(
            "fixture.ps1", "& $wrapper clean test"
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("through bash", findings[0])


if __name__ == "__main__":
    unittest.main()
