from __future__ import annotations

import ssl
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import r4_vke_connectivity_diagnostic as diagnostic


class VkeConnectivityDiagnosticTests(unittest.TestCase):
    def test_endpoint_requires_https_and_rejects_userinfo(self) -> None:
        with self.assertRaises(diagnostic.DiagnosticInputError):
            diagnostic.parse_endpoint("http://cluster.example:6443")
        with self.assertRaises(diagnostic.DiagnosticInputError):
            diagnostic.parse_endpoint("https://user:pass@cluster.example:6443")

    def test_endpoint_defaults_to_https_port_and_preserves_hostname(self) -> None:
        endpoint = diagnostic.parse_endpoint("https://Cluster.Example")
        self.assertEqual(endpoint.scheme, "https")
        self.assertEqual(endpoint.hostname, "cluster.example")
        self.assertEqual(endpoint.port, 443)

    def test_ip_classification_distinguishes_fake_private_and_public(self) -> None:
        self.assertEqual(diagnostic.classify_ip("198.18.0.40"), "FAKE_DNS")
        self.assertEqual(diagnostic.classify_ip("10.0.0.4"), "PRIVATE")
        self.assertEqual(diagnostic.classify_ip("1.1.1.1"), "PUBLIC")

    def test_source_cidr_match_is_fail_closed_for_invalid_or_missing_values(self) -> None:
        self.assertTrue(diagnostic._source_cidr_match("1.2.3.4", "1.2.3.4/32"))
        self.assertFalse(diagnostic._source_cidr_match("1.2.3.5", "1.2.3.4/32"))
        self.assertIsNone(diagnostic._source_cidr_match("1.2.3.4", None))
        self.assertIsNone(diagnostic._source_cidr_match("not-an-ip", "1.2.3.4/32"))

    def test_tls_exception_classes_are_not_collapsed(self) -> None:
        self.assertEqual(diagnostic._failure_status(ssl.SSLEOFError()), "TLS_EOF")
        self.assertEqual(diagnostic._failure_status(ConnectionResetError()), "TLS_RESET")
        self.assertEqual(diagnostic._failure_status(TimeoutError()), "TLS_TIMEOUT")
        self.assertEqual(
            diagnostic._failure_status(ssl.SSLCertVerificationError()),
            "TLS_CERT_FAILURE",
        )

    def test_kubeconfig_server_reader_only_extracts_server_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kubeconfig.yaml"
            path.write_text(
                "clusters:\n- cluster:\n    server: https://cluster.example:6443\n"
                "    certificate-authority-data: SECRET_MATERIAL\n",
                encoding="utf-8",
            )
            self.assertEqual(
                diagnostic.read_kubeconfig_server(path), "https://cluster.example:6443"
            )

    def test_kubeconfig_multiple_servers_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kubeconfig.yaml"
            path.write_text(
                "server: https://one.example\nserver: https://two.example\n",
                encoding="utf-8",
            )
            with self.assertRaises(diagnostic.DiagnosticInputError):
                diagnostic.read_kubeconfig_server(path)

    def test_fake_dns_resolution_can_be_explicitly_overridden_for_connectivity(self) -> None:
        report = diagnostic.endpoint_report(
            diagnostic.parse_endpoint("https://cluster.example:6443"),
            "1.1.1.1",
            None,
            None,
            "1.1.1.1/32",
        )
        self.assertEqual(report["port"], 6443)
        self.assertEqual(report["tlsServerName"], "cluster.example")
        self.assertTrue(report["sniMatchesEndpointHostname"])

    def test_proxy_environment_uses_unique_case_insensitive_keys(self) -> None:
        with mock.patch.dict(diagnostic.os.environ, {"all_proxy": "configured"}, clear=False):
            report = diagnostic.inspect_proxy_environment()
        self.assertEqual(report["environment"]["ALL_PROXY"], "SET")
        self.assertNotIn("all_proxy", report["environment"])
        self.assertEqual(len(report["environment"]), len(set(report["environment"])))


if __name__ == "__main__":
    unittest.main()
