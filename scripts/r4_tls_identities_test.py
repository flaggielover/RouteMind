from __future__ import annotations

import copy
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import r4_tls_identities as tls


class TlsIdentityTests(unittest.TestCase):
    def test_frozen_identity_plan_is_valid(self) -> None:
        result = tls.validate_identities(tls.TLS_IDENTITIES)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["identities"]), 4)
        self.assertLessEqual(
            max(
                len(item["commonName"].encode("utf-8")) for item in result["identities"]
            ),
            64,
        )

    def test_long_dns_name_is_allowed_in_san_with_short_common_name(self) -> None:
        result = tls.validate_identities(tls.TLS_IDENTITIES)
        signoz = next(item for item in result["identities"] if item["name"] == "signoz")
        self.assertGreater(len(signoz["dnsName"]), 64)
        self.assertLessEqual(len(signoz["commonName"]), 64)

    def test_long_common_name_is_rejected(self) -> None:
        mutated = copy.deepcopy(tls.TLS_IDENTITIES)
        mutated[0]["commonName"] = "x" * 65
        with self.assertRaisesRegex(tls.TlsIdentityError, "64-byte"):
            tls.validate_identities(mutated)

    def test_server_identity_without_dns_san_is_rejected(self) -> None:
        mutated = copy.deepcopy(tls.TLS_IDENTITIES)
        del mutated[0]["dnsName"]
        with self.assertRaisesRegex(tls.TlsIdentityError, "DNS SAN"):
            tls.validate_identities(mutated)

    def test_client_identity_with_server_dns_san_is_rejected(self) -> None:
        mutated = copy.deepcopy(tls.TLS_IDENTITIES)
        mutated[2]["dnsName"] = "unexpected.example"
        with self.assertRaisesRegex(tls.TlsIdentityError, "must not"):
            tls.validate_identities(mutated)

    def test_openssl_accepts_short_cn_and_full_dns_san(self) -> None:
        openssl = shutil.which("openssl")
        if openssl is None:
            self.skipTest("OpenSSL is not on PATH")
        identity = tls.validate_identities(tls.TLS_IDENTITIES)["identities"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = root / "key.pem"
            request = root / "request.pem"
            cert = root / "cert.pem"
            extension = root / "server.ext"
            extension.write_text(
                f"extendedKeyUsage=serverAuth\nsubjectAltName=DNS:{identity['dnsName']}\n",
                encoding="ascii",
            )
            subprocess.run(
                [
                    openssl,
                    "req",
                    "-new",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(key),
                    "-out",
                    str(request),
                    "-subj",
                    f"/CN={identity['commonName']}",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    openssl,
                    "x509",
                    "-req",
                    "-in",
                    str(request),
                    "-signkey",
                    str(key),
                    "-out",
                    str(cert),
                    "-days",
                    "1",
                    "-sha256",
                    "-extfile",
                    str(extension),
                ],
                check=True,
                capture_output=True,
            )
            inspection = subprocess.run(
                [
                    openssl,
                    "x509",
                    "-in",
                    str(cert),
                    "-noout",
                    "-subject",
                    "-ext",
                    "subjectAltName",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertRegex(
                inspection,
                rf"subject=CN\s*=\s*{re.escape(identity['commonName'])}",
            )
            self.assertIn(f"DNS:{identity['dnsName']}", inspection)


if __name__ == "__main__":
    unittest.main()
