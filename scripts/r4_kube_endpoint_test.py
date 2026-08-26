from __future__ import annotations

import unittest

import r4_kube_endpoint as endpoint


class KubeEndpointTests(unittest.TestCase):
    def test_normal_dns_resolution_is_preserved(self) -> None:
        self.assertIsNone(
            endpoint.choose_endpoint_rewrite(
                "https://cluster.example:6443", ["8.8.8.8"], "1.1.1.1"
            )
        )

    def test_fake_dns_resolution_uses_provider_ip_and_preserves_tls_name(self) -> None:
        rewrite = endpoint.choose_endpoint_rewrite(
            "https://cluster.example:6443", ["198.18.0.27"], "1.1.1.1"
        )
        self.assertIsNotNone(rewrite)
        assert rewrite is not None
        self.assertEqual(rewrite.server, "https://1.1.1.1:6443")
        self.assertEqual(rewrite.tls_server_name, "cluster.example")

    def test_mixed_real_and_fake_resolution_is_not_rewritten(self) -> None:
        self.assertIsNone(
            endpoint.choose_endpoint_rewrite(
                "https://cluster.example:6443",
                ["198.18.0.27", "8.8.8.8"],
                "1.1.1.1",
            )
        )

    def test_private_provider_ip_is_rejected(self) -> None:
        with self.assertRaisesRegex(endpoint.KubeEndpointError, "public IPv4"):
            endpoint.choose_endpoint_rewrite(
                "https://cluster.example:6443", ["198.18.0.27"], "10.0.0.1"
            )

    def test_non_https_server_is_rejected(self) -> None:
        with self.assertRaisesRegex(endpoint.KubeEndpointError, "HTTPS"):
            endpoint.choose_endpoint_rewrite(
                "http://cluster.example:6443", ["198.18.0.27"], "1.1.1.1"
            )


if __name__ == "__main__":
    unittest.main()
