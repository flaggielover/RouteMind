from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthPasswordRemoteForwardCommand.java"
CLI = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthPasswordRemoteForwardProbeCli.java"
SCRIPT = ROOT / "scripts/gmail-oauth-remote-forward-password-probe.ps1"
CONFIG = ROOT / "services/business-api/src/main/java/com/routemind/business/infrastructure/notification/GmailOAuthPasswordRemoteForwardConfiguration.java"
VERIFY = ROOT / "scripts/verify.ps1"


class GmailOAuthPasswordRemoteForwardBoundaryTests(unittest.TestCase):
    def test_command_enables_only_native_interactive_password(self) -> None:
        command = COMMAND.read_text(encoding="utf-8")
        for option in (
            "BatchMode=no",
            "StrictHostKeyChecking=yes",
            "CheckHostIP=yes",
            "PubkeyAuthentication=no",
            "PasswordAuthentication=yes",
            "KbdInteractiveAuthentication=yes",
            "PreferredAuthentications=keyboard-interactive,password",
            "NumberOfPasswordPrompts=1",
            "ExitOnForwardFailure=yes",
        ):
            self.assertIn(option, command)
        for forbidden in ("IdentityFile", "IdentitiesOnly", "sshpass", "expect", "-pw", "0.0.0.0", '"-g"'):
            self.assertNotIn(forbidden, command)
        self.assertIn('"127.0.0.1:" + macPort + ":127.0.0.1:" + windowsPort', command)
        self.assertIn('MAC_USER + "@"', command)
        self.assertIn('MAC_HOST', command)

    def test_process_inherits_console_input_and_does_not_capture_password(self) -> None:
        cli = CLI.read_text(encoding="utf-8")
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("redirectInput(ProcessBuilder.Redirect.INHERIT)", cli)
        self.assertIn("redirectError(ProcessBuilder.Redirect.INHERIT)", cli)
        self.assertIn("redirectOutput(ProcessBuilder.Redirect.DISCARD)", cli)
        self.assertIn("type it manually", cli)
        self.assertNotIn("readPassword", cli)
        self.assertNotIn("getPassword", cli)
        self.assertNotIn("SecureString", script)
        self.assertNotIn("SSHPASS", script)
        self.assertNotIn("Password=", script)

    def test_synthetic_probe_cannot_start_oauth(self) -> None:
        cli = CLI.read_text(encoding="utf-8")
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("/synthetic-probe", cli)
        self.assertIn("OAuth was not started", cli)
        self.assertNotIn("GmailOAuthBootstrapConfiguration", cli)
        self.assertNotIn("AuthorizationCodeRequestUrl", cli)
        self.assertNotIn("gmail.send", cli)
        self.assertNotIn("ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE", script)
        self.assertNotIn("gmail-oauth-bootstrap-remote.ps1", VERIFY.read_text(encoding="utf-8"))

    def test_fixed_target_and_port_configuration(self) -> None:
        config = CONFIG.read_text(encoding="utf-8")
        self.assertIn('MAC_HOST = "10.10.1.27"', config)
        self.assertIn('MAC_USER = "suzhe"', config)
        self.assertIn("between 1024 and 65535", config)
        self.assertIn("ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS", config)


if __name__ == "__main__":
    unittest.main()
