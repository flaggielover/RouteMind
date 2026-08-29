from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthRemoteBootstrapCli.java"
COMMAND = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthRemoteForwardCommand.java"
CONFIG = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthRemoteForwardConfiguration.java"
POLICY = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthRemoteForwardPolicy.java"
SCRIPT = ROOT / "scripts/gmail-oauth-bootstrap-remote.ps1"
VERIFY = ROOT / "scripts/verify.ps1"


class GmailOAuthRemoteForwardBoundaryTests(unittest.TestCase):
    def test_remote_command_is_explicit_and_not_a_verify_step(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GmailOAuthRemoteBootstrapCli", script)
        self.assertIn("ROUTEMIND_GMAIL_OAUTH_MAC_SSH_KEY_PATH", script)
        self.assertIn("ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS", script)
        self.assertIn("ROUTEMIND_GMAIL_OAUTH_MAC_PORT", script)
        self.assertNotIn("users.messages.send", script)
        self.assertNotIn("gmail-oauth-bootstrap-remote.ps1", VERIFY.read_text(encoding="utf-8"))

    def test_cli_constructs_only_strict_remote_forward(self) -> None:
        cli = CLI.read_text(encoding="utf-8")
        command = COMMAND.read_text(encoding="utf-8")
        self.assertIn("GmailOAuthRemoteForwardCommand.build", cli)
        for option in ("StrictHostKeyChecking=yes", "CheckHostIP=yes", "IdentitiesOnly=yes", "ExitOnForwardFailure=yes"):
            self.assertIn(option, command)
        self.assertIn('"127.0.0.1:" + macPort + ":127.0.0.1:" + windowsPort', command)
        self.assertIn('MAC_USER + "@"', command)
        self.assertIn('MAC_HOST', command)
        self.assertNotIn("0.0.0.0", command)
        self.assertNotIn('"-g"', command)
        self.assertNotIn("users.messages.send", cli)

    def test_paths_are_external_and_configuration_is_bounded(self) -> None:
        config = CONFIG.read_text(encoding="utf-8")
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("must be between 1024 and 65535", config)
        self.assertIn("must be outside the repository", policy)
        self.assertIn("redirects through a link", policy)


if __name__ == "__main__":
    unittest.main()
