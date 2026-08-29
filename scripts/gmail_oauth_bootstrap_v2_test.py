from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthBootstrapV2Cli.java"
SESSION = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthBootstrapV2Session.java"
INSTRUCTIONS = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthOperatorTunnelInstructions.java"
SCRIPT = ROOT / "scripts/gmail-oauth-bootstrap-v2.ps1"
VERIFY = ROOT / "scripts/verify.ps1"


class GmailOAuthBootstrapV2BoundaryTests(unittest.TestCase):
    def test_v2_script_is_explicit_and_not_a_verify_step(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        self.assertIn("GmailOAuthBootstrapV2Cli", script)
        self.assertIn("spring-boot:run", script)
        self.assertNotIn("GmailOAuthBootstrapV2Cli", verify)

    def test_cli_never_starts_ssh_or_reads_password(self) -> None:
        cli = CLI.read_text(encoding="utf-8")
        self.assertIn("GmailOAuthOperatorTunnelInstructions", cli)
        self.assertIn("GmailOAuthBootstrapV2Session.PREFLIGHT_PATH", cli)
        self.assertNotIn("ProcessBuilder", cli)
        self.assertNotIn("ssh.exe", cli)
        self.assertNotIn("System.console", cli)
        self.assertNotIn("System.in", cli)

    def test_authorization_url_is_after_preflight_gate(self) -> None:
        cli = CLI.read_text(encoding="utf-8")
        self.assertLess(cli.index("await(preflight"), cli.index("authorizationUrl(flow"))
        session = SESSION.read_text(encoding="utf-8")
        self.assertIn("routemind-oauth-preflight", session)
        self.assertIn("OAuth authorization URL requires tunnel preflight", session)
        self.assertIn("PREFLIGHT_RESPONSE", session)

    def test_manual_command_is_loopback_only_and_password_external(self) -> None:
        instructions = INSTRUCTIONS.read_text(encoding="utf-8")
        self.assertIn("StrictHostKeyChecking=yes", instructions)
        self.assertIn("CheckHostIP=yes", instructions)
        self.assertIn("127.0.0.1:", instructions)
        self.assertIn("suzhe@10.10.1.27", instructions)
        self.assertNotIn("IdentityFile", instructions)
        self.assertNotIn("sshpass", instructions)
        self.assertNotIn("password", instructions.lower())


if __name__ == "__main__":
    unittest.main()
