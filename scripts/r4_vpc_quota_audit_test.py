from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "r4_vpc_quota_audit.ps1"


class VpcQuotaAuditScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SCRIPT.read_text(encoding="utf-8")

    def test_provider_calls_are_get_only(self) -> None:
        methods = re.findall(r"Invoke-RestMethod\s+-Method\s+([A-Za-z]+)", self.source)
        self.assertEqual(methods, ["Get"])
        for forbidden in ("-Method Post", "-Method Put", "-Method Patch", "-Method Delete"):
            self.assertNotIn(forbidden, self.source)

    def test_audit_covers_vpcs_and_related_resource_classes(self) -> None:
        for endpoint in (
            "/vpcs?per_page=500",
            "/instances?per_page=500",
            "/kubernetes/clusters?per_page=500",
            "/load-balancers?per_page=500",
            "/bare-metals?per_page=500",
            "/databases?per_page=500",
        ):
            self.assertIn(endpoint, self.source)

    def test_reuse_and_unused_inferences_fail_closed(self) -> None:
        self.assertIn('ownership = "UNKNOWN"', self.source)
        self.assertIn('apparentlyUnused = "UNKNOWN"', self.source)
        self.assertIn('safeReuse = "NOT_SAFE_TO_REUSE"', self.source)
        self.assertIn('mutationPerformed = $false', self.source)

    def test_secret_is_never_serialized(self) -> None:
        self.assertNotRegex(self.source, r"(?m)^\s*apiKey\s*=")
        self.assertIn("$apiKey = $null", self.source)


if __name__ == "__main__":
    unittest.main()
