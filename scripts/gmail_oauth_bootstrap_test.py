from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthBootstrapCli.java"
SCRIPT = ROOT / "scripts/gmail-oauth-bootstrap.ps1"
VERIFY = ROOT / "scripts/verify.ps1"
APPLICATION = ROOT / "services/business-api/src/main/resources/application.yml"


class GmailOAuthBootstrapBoundaryTests(unittest.TestCase):
    def test_bootstrap_command_is_explicit_and_not_a_verify_step(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GmailOAuthBootstrapCli", script)
        self.assertIn("spring-boot:run", script)
        self.assertNotIn("users.messages.send", script)
        self.assertNotIn("gmail-oauth-bootstrap.ps1", VERIFY.read_text(encoding="utf-8"))

    def test_cli_has_no_message_adapter_or_startup_wiring(self) -> None:
        cli = CLI.read_text(encoding="utf-8")
        self.assertNotIn("Gmail.Users", cli)
        self.assertNotIn("users.messages.send", cli)
        self.assertIn("GmailOAuthBootstrapConfiguration", cli)
        self.assertIn("fromEnvironment(System.getenv())", cli)
        self.assertIn("127.0.0.1", cli)

    def test_runtime_stays_disabled_by_default(self) -> None:
        application = APPLICATION.read_text(encoding="utf-8")
        self.assertIn("enabled: ${ROUTEMIND_NOTIFICATION_GMAIL_ENABLED:false}", application)
        self.assertIn("ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE", application)
        self.assertIn("ROUTEMIND_GMAIL_TOKEN_STORE", application)


if __name__ == "__main__":
    unittest.main()
