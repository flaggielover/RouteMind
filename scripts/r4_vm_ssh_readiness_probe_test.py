from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from r4_ssh_readiness import classify
from r4_vm_ssh_readiness_probe import pin_known_host, probe_tcp_banner, run_strict_ssh


class Connection:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def settimeout(self, _: float) -> None:
        return None

    def recv(self, _: int) -> bytes:
        return self.payload


class ProbeTest(unittest.TestCase):
    @patch("r4_vm_ssh_readiness_probe.socket.gethostbyname", return_value="203.0.113.7")
    @patch("r4_vm_ssh_readiness_probe.socket.create_connection", side_effect=TimeoutError)
    def test_tcp_timeout(self, *_: MagicMock) -> None:
        self.assertEqual("TIMEOUT", probe_tcp_banner("example.invalid")["tcp"])

    @patch("r4_vm_ssh_readiness_probe.socket.gethostbyname", return_value="203.0.113.7")
    @patch("r4_vm_ssh_readiness_probe.socket.create_connection", side_effect=ConnectionResetError)
    def test_tcp_reset(self, *_: MagicMock) -> None:
        self.assertEqual("RESET", probe_tcp_banner("example.invalid")["tcp"])

    def test_banner_classes(self) -> None:
        for payload, expected in (
            (b"", "MISSING"),
            (b"HTTP/1.1 200 OK\r\n", "MALFORMED"),
            (b"SSH-2.0-OpenSSH_9.6p1\r\n", "VALID"),
        ):
            with self.subTest(expected=expected), patch(
                "r4_vm_ssh_readiness_probe.socket.gethostbyname",
                return_value="203.0.113.7",
            ), patch(
                "r4_vm_ssh_readiness_probe.socket.create_connection",
                return_value=Connection(payload),
            ):
                self.assertEqual(expected, probe_tcp_banner("example.invalid")["banner"])

    @patch("r4_vm_ssh_readiness_probe.known_hosts_has_fingerprint", return_value=False)
    @patch("r4_vm_ssh_readiness_probe.subprocess.run")
    def test_unpinned_host_stops_before_auth(self, run: MagicMock, _: MagicMock) -> None:
        run.return_value = subprocess.CompletedProcess(
            [], 255, "", "debug1: SSH2_MSG_KEXINIT sent\nHost key verification failed."
        )
        observation, raw, guest = self._run()
        self.assertEqual("SSH_HOST_KEY_ABSENT", classify(observation))
        self.assertFalse(raw["authStarted"])
        self.assertIsNone(guest)

    @patch("r4_vm_ssh_readiness_probe.known_hosts_has_fingerprint", return_value=True)
    @patch("r4_vm_ssh_readiness_probe.subprocess.run", side_effect=subprocess.TimeoutExpired("ssh", 20))
    def test_kex_timeout_is_retained(self, _: MagicMock, __: MagicMock) -> None:
        observation, raw, guest = self._run()
        self.assertEqual("SSH_KEX_TIMEOUT", classify(observation))
        self.assertEqual("TIMEOUT", raw["ssh"])
        self.assertIsNone(guest)

    @patch("r4_vm_ssh_readiness_probe.known_hosts_has_fingerprint", return_value=True)
    @patch("r4_vm_ssh_readiness_probe.subprocess.run")
    def test_changed_host_key_is_distinct(self, run: MagicMock, _: MagicMock) -> None:
        run.return_value = subprocess.CompletedProcess(
            [], 255, "", "debug1: SSH2_MSG_KEXINIT sent\nREMOTE HOST IDENTIFICATION HAS CHANGED"
        )
        observation, _, _ = self._run()
        self.assertEqual("SSH_HOST_KEY_CHANGED", classify(observation))

    @patch("r4_vm_ssh_readiness_probe.known_hosts_has_fingerprint", return_value=True)
    @patch("r4_vm_ssh_readiness_probe.subprocess.run")
    def test_auth_rejection_is_after_verified_host(self, run: MagicMock, _: MagicMock) -> None:
        run.return_value = subprocess.CompletedProcess(
            [],
            255,
            "",
            "debug1: SSH2_MSG_KEXINIT sent\ndebug1: Host 'x' is known and matches\nAuthentications that can continue: publickey",
        )
        observation, _, _ = self._run()
        self.assertEqual("SSH_AUTH_REJECTED", classify(observation))

    @patch("r4_vm_ssh_readiness_probe.known_hosts_has_fingerprint", return_value=True)
    @patch("r4_vm_ssh_readiness_probe.subprocess.run")
    def test_ready_requires_canonical_guest_artifact(self, run: MagicMock, _: MagicMock) -> None:
        guest = {
            "schema": "r4-vm-ssh-readiness-guest-artifact.v1",
            "cloudInitStatus": "status: done",
            "authorizedKeyFingerprintMatch": True,
            "sshListenerPresent": True,
            "sshdConfigValid": True,
            "sshServiceActive": True,
        }
        run.return_value = subprocess.CompletedProcess(
            [],
            0,
            json.dumps(guest),
            "debug1: SSH2_MSG_KEXINIT sent\ndebug1: Host 'x' is known and matches\nOffering public key",
        )
        observation, _, parsed = self._run()
        self.assertEqual("READY", classify(observation))
        self.assertEqual(guest, parsed)

    @patch("r4_vm_ssh_readiness_probe.known_hosts_has_fingerprint", return_value=True)
    @patch("r4_vm_ssh_readiness_probe.subprocess.run")
    def test_host_key_is_pinned_only_after_fingerprint_match(
        self, run: MagicMock, _: MagicMock
    ) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 0, "203.0.113.7 ssh-ed25519 AAAATEST\n", ""),
            subprocess.CompletedProcess([], 0, "256 SHA256:server test (ED25519)\n", ""),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "known_hosts"
            self.assertTrue(
                pin_known_host(
                    host="203.0.113.7",
                    expected_host_key_sha256="SHA256:server",
                    destination=path,
                    timeout_seconds=10,
                )
            )
            self.assertEqual("203.0.113.7 ssh-ed25519 AAAATEST\n", path.read_text(encoding="utf-8"))

    @patch("r4_vm_ssh_readiness_probe.subprocess.run")
    def test_host_key_mismatch_is_not_persisted(self, run: MagicMock) -> None:
        run.side_effect = [
            subprocess.CompletedProcess([], 0, "203.0.113.7 ssh-ed25519 AAAATEST\n", ""),
            subprocess.CompletedProcess([], 0, "256 SHA256:other test (ED25519)\n", ""),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "known_hosts"
            self.assertFalse(
                pin_known_host(
                    host="203.0.113.7",
                    expected_host_key_sha256="SHA256:server",
                    destination=path,
                    timeout_seconds=10,
                )
            )
            self.assertFalse(path.exists())

    @staticmethod
    def _run():  # type: ignore[no-untyped-def]
        return run_strict_ssh(
            host="203.0.113.7",
            username="root",
            private_key=Path("outside-repo-key"),
            known_hosts=Path("known-hosts"),
            expected_host_key_sha256="SHA256:test",
            timeout_seconds=10,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
