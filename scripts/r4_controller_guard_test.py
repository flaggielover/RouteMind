from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ControllerGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controller = (ROOT / "scripts" / "r4_external_validation.ps1").read_text(
            encoding="utf-8"
        )
        cls.terraform = (
            ROOT / "infra" / "external-validation" / "vultr-tokyo" / "outputs.tf"
        ).read_text(encoding="utf-8")

    def test_runtime_uses_validated_tls_identity_plan(self) -> None:
        self.assertTrue(self.controller.startswith("#Requires -Version 7.0"))
        self.assertIn("$TlsIdentityScript", self.controller)
        self.assertIn("$identityPlan.identities", self.controller)
        self.assertIn('"subjectAltName=DNS:$($identity.dnsName)"', self.controller)

    def test_runtime_repairs_only_fake_dns_kube_endpoint(self) -> None:
        self.assertIn("$KubeEndpointScript", self.controller)
        self.assertIn("--provider-ip", self.controller)
        self.assertIn("vke_ip", self.terraform)

    def test_kubernetes_mutation_marker_precedes_first_apply(self) -> None:
        marker = self.controller.index(
            "Set-Content -LiteralPath $Paths.KubernetesMutationStarted"
        )
        first_apply = self.controller.index(
            'Invoke-Native "kubectl" @("apply", "-f", (Join-Path $IacRoot "namespace-boundaries.yaml"))'
        )
        self.assertLess(marker, first_apply)

    def test_cleanup_removes_state_backup_and_retries_inventory(self) -> None:
        self.assertIn("$Paths.TerraformStateBackup", self.controller)
        self.assertIn(
            "Credentialed cleanup inventory did not converge", self.controller
        )


if __name__ == "__main__":
    unittest.main()
