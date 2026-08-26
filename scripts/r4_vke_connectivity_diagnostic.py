"""Read-only, phase-labelled diagnostics for a Vultr VKE API endpoint.

The probe never reads credentials or uses an HTTP proxy.  It resolves the
endpoint, opens a direct TCP connection, performs a TLS handshake with the
requested SNI name, and only then sends an unauthenticated Kubernetes
``/version`` request.  Network failures are reports, not pass claims.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import platform
import re
import socket
import ssl
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

FAKE_DNS_NETWORK = ipaddress.ip_network("198.18.0.0/15")
PROXY_NAMES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)
STATUS_LINE = re.compile(r"^HTTP/1\.[01]\s+(\d{3})(?:\s|$)")


class DiagnosticInputError(ValueError):
    pass


@dataclass(frozen=True)
class Endpoint:
    scheme: str
    hostname: str
    port: int


@dataclass(frozen=True)
class Address:
    value: str
    family: str
    classification: str


def parse_endpoint(value: str) -> Endpoint:
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise DiagnosticInputError("endpoint must be an HTTPS URL with a hostname")
    if parsed.username or parsed.password:
        raise DiagnosticInputError("endpoint userinfo is not allowed")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise DiagnosticInputError("endpoint port is invalid") from exc
    if not 1 <= port <= 65535:
        raise DiagnosticInputError("endpoint port is outside the TCP range")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise DiagnosticInputError("endpoint must not contain a path, query, or fragment")
    return Endpoint(parsed.scheme.lower(), parsed.hostname, port)


def classify_ip(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return "INVALID"
    if address in FAKE_DNS_NETWORK:
        return "FAKE_DNS"
    if address.is_loopback:
        return "LOOPBACK"
    if address.is_link_local:
        return "LINK_LOCAL"
    if address.is_private:
        return "PRIVATE"
    if address.is_global:
        return "PUBLIC"
    return "SPECIAL"


def _family_name(family: socket.AddressFamily) -> str:
    if family == socket.AF_INET:
        return "IPv4"
    if family == socket.AF_INET6:
        return "IPv6"
    return str(int(family))


def resolve_addresses(hostname: str, port: int) -> list[Address]:
    try:
        records = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror:
        return []
    seen: set[tuple[str, int]] = set()
    result: list[Address] = []
    for family, _socktype, _proto, _canonname, sockaddr in records:
        value = sockaddr[0]
        key = (value, int(family))
        if key in seen:
            continue
        seen.add(key)
        result.append(
            Address(value, _family_name(family), classify_ip(value))
        )
    return result


def _source_cidr_match(source: str | None, cidr: str | None) -> bool | None:
    if not source or not cidr:
        return None
    try:
        return ipaddress.ip_address(source) in ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return None


def _source_class(source: str | None) -> str:
    return classify_ip(source) if source else "UNKNOWN"


def _failure_status(exc: BaseException) -> str:
    if isinstance(exc, ssl.SSLEOFError):
        return "TLS_EOF"
    if isinstance(exc, ConnectionResetError):
        return "TLS_RESET"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "TLS_TIMEOUT"
    if isinstance(exc, ssl.SSLCertVerificationError):
        return "TLS_CERT_FAILURE"
    if isinstance(exc, ssl.SSLError):
        return "TLS_ERROR"
    return "TLS_FAIL"


def _direct_tls_context(ca_file: Path | None) -> ssl.SSLContext:
    if ca_file is None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    context = ssl.create_default_context(cafile=str(ca_file))
    context.check_hostname = True
    return context


def _http_status(sock: ssl.SSLSocket, hostname: str, path: str) -> dict[str, Any]:
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {hostname}\r\n"
        "Connection: close\r\n"
        "User-Agent: routemind-r4-vke-diagnostic/1\r\n\r\n"
    ).encode("ascii")
    try:
        sock.sendall(request)
        first_line = sock.makefile("rb", buffering=0).readline(256).decode(
            "ascii", errors="replace"
        ).strip()
    except Exception as exc:  # pragma: no cover - platform/network dependent
        return {"status": "HTTP_FAIL", "errorType": type(exc).__name__}
    match = STATUS_LINE.match(first_line)
    if not match:
        return {"status": "HTTP_FAIL", "errorType": "INVALID_STATUS_LINE"}
    return {"status": "HTTP_OK", "statusCode": int(match.group(1))}


def probe_address(
    address: Address,
    endpoint: Endpoint,
    tls_server_name: str,
    timeout: float,
    ca_file: Path | None,
    http_path: str,
    operator_cidr: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "address": asdict(address),
        "tcp": {"status": "TCP_FAIL"},
        "tls": {"status": "TLS_NOT_ATTEMPTED", "helloSent": False},
        "http": {"status": "HTTP_NOT_ATTEMPTED"},
    }
    family = socket.AF_INET6 if address.family == "IPv6" else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    started = time.monotonic()
    try:
        sock.connect((address.value, endpoint.port))
        source = sock.getsockname()[0]
        result["tcp"] = {
            "status": "TCP_OK",
            "sourceClass": _source_class(source),
            "operatorCidrMatch": _source_cidr_match(source, operator_cidr),
            "elapsedMs": round((time.monotonic() - started) * 1000, 3),
        }
    except Exception as exc:  # pragma: no cover - platform/network dependent
        result["tcp"] = {
            "status": "TCP_FAIL",
            "errorType": type(exc).__name__,
            "elapsedMs": round((time.monotonic() - started) * 1000, 3),
        }
        sock.close()
        return result

    tls_started = time.monotonic()
    result["tls"]["helloSent"] = True
    try:
        context = _direct_tls_context(ca_file)
        tls_sock = context.wrap_socket(sock, server_hostname=tls_server_name)
        result["tls"] = {
            "status": "TLS_OK",
            "helloSent": True,
            "sni": tls_server_name,
            "verification": "verified" if ca_file else "handshake_only",
            "elapsedMs": round((time.monotonic() - tls_started) * 1000, 3),
        }
        result["http"] = _http_status(tls_sock, endpoint.hostname, http_path)
        tls_sock.close()
    except Exception as exc:  # pragma: no cover - platform/network dependent
        result["tls"] = {
            "status": _failure_status(exc),
            "helloSent": True,
            "sni": tls_server_name,
            "verification": "verified" if ca_file else "handshake_only",
            "errorType": type(exc).__name__,
            "elapsedMs": round((time.monotonic() - tls_started) * 1000, 3),
        }
        try:
            sock.close()
        except OSError:
            pass
    return result


def inspect_proxy_environment() -> dict[str, Any]:
    return {
        "environment": {
            name: "SET" if os.environ.get(name) else "MISSING" for name in PROXY_NAMES
        },
        "winhttp": _winhttp_proxy_state(),
        "systemProxy": "NOT_PROBED_BY_THIS_TOOL",
    }


def _winhttp_proxy_state() -> str:
    if platform.system() != "Windows":
        return "UNAVAILABLE"
    try:
        completed = subprocess.run(
            ["netsh", "winhttp", "show", "proxy"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"
    output = f"{completed.stdout}\n{completed.stderr}"
    if re.search(r"Direct access\s*\(no proxy server\)", output, re.I):
        return "DIRECT"
    return "CONFIGURED" if completed.returncode == 0 else "UNKNOWN"


def read_kubeconfig_server(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    servers: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        match = re.match(r"^\s*server:\s*(\S+)\s*$", line)
        if match:
            servers.append(match.group(1))
    if len(servers) > 1:
        raise DiagnosticInputError("kubeconfig contains more than one server")
    return servers[0] if servers else None


def endpoint_report(
    endpoint: Endpoint,
    connect_host: str | None,
    tls_server_name: str | None,
    kubeconfig: Path | None,
    operator_cidr: str | None,
) -> dict[str, Any]:
    resolved = resolve_addresses(endpoint.hostname, endpoint.port)
    kube_server = read_kubeconfig_server(kubeconfig)
    tls_name = tls_server_name or endpoint.hostname
    connect_addresses = resolved
    if connect_host:
        resolved_connect = resolve_addresses(connect_host, endpoint.port)
        if not resolved_connect:
            try:
                parsed = ipaddress.ip_address(connect_host)
            except ValueError:
                resolved_connect = []
            else:
                resolved_connect = [
                    Address(connect_host, "IPv6" if parsed.version == 6 else "IPv4", classify_ip(connect_host))
                ]
        connect_addresses = resolved_connect
    endpoint_identity = f"{endpoint.scheme}://{endpoint.hostname}:{endpoint.port}"
    return {
        "scheme": endpoint.scheme,
        "hostname": endpoint.hostname,
        "port": endpoint.port,
        "endpoint": endpoint_identity,
        "tlsServerName": tls_name,
        "sniMatchesEndpointHostname": tls_name.lower() == endpoint.hostname.lower(),
        "resolvedAddresses": [asdict(item) for item in resolved],
        "publicResolution": any(item.classification == "PUBLIC" for item in resolved),
        "privateResolution": any(item.classification == "PRIVATE" for item in resolved),
        "fakeDnsResolution": any(item.classification == "FAKE_DNS" for item in resolved),
        "connectHost": connect_host or endpoint.hostname,
        "connectAddresses": [asdict(item) for item in connect_addresses],
        "kubeconfigServer": kube_server,
        "kubeconfigMatchesEndpoint": kube_server == endpoint_identity if kube_server else None,
        "operatorCidrConfigured": "SET" if operator_cidr else "MISSING",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    endpoint = parse_endpoint(args.endpoint)
    operator_cidr = os.environ.get("ROUTEMIND_OPERATOR_CIDR")
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "tool": "r4-vke-connectivity-diagnostic",
        "observedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": endpoint_report(
            endpoint,
            args.connect_host,
            args.tls_server_name,
            args.kubeconfig,
            operator_cidr,
        ),
        "proxy": inspect_proxy_environment(),
        "probes": [],
    }
    addresses = report["endpoint"]["connectAddresses"]
    for item in addresses[: args.max_addresses]:
        address = Address(item["value"], item["family"], item["classification"])
        report["probes"].append(
            probe_address(
                address,
                endpoint,
                report["endpoint"]["tlsServerName"],
                args.timeout,
                args.ca_file,
                args.http_path,
                operator_cidr,
            )
        )
    report["summary"] = {
        "dns": "DNS_OK" if report["endpoint"]["resolvedAddresses"] else "DNS_FAIL",
        "tcp": "TCP_OK" if any(p["tcp"]["status"] == "TCP_OK" for p in report["probes"]) else "TCP_FAIL",
        "tlsHelloSent": any(p["tls"].get("helloSent") for p in report["probes"]),
        "tls": next(
            (p["tls"]["status"] for p in report["probes"] if p["tls"]["status"] != "TLS_NOT_ATTEMPTED"),
            "TLS_NOT_ATTEMPTED",
        ),
        "http": next(
            (p["http"]["status"] for p in report["probes"] if p["http"]["status"] != "HTTP_NOT_ATTEMPTED"),
            "HTTP_NOT_ATTEMPTED",
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="HTTPS VKE API endpoint")
    parser.add_argument("--connect-host", help="Direct IP/hostname override; SNI is preserved")
    parser.add_argument("--tls-server-name", help="SNI name; defaults to endpoint hostname")
    parser.add_argument("--kubeconfig", type=Path, help="Optional kubeconfig; only server lines are read")
    parser.add_argument("--ca-file", type=Path, help="Optional CA for verified TLS validation")
    parser.add_argument("--http-path", default="/version")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-addresses", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Emit compact JSON")
    args = parser.parse_args()
    if not 0.1 <= args.timeout <= 30:
        parser.error("--timeout must be between 0.1 and 30 seconds")
    if not 1 <= args.max_addresses <= 8:
        parser.error("--max-addresses must be between 1 and 8")
    try:
        report = run(args)
    except (DiagnosticInputError, OSError) as exc:
        parser.error(str(exc))
    output = json.dumps(report, sort_keys=True, separators=(",", ":") if args.json else None)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
