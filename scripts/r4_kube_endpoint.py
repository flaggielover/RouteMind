from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

FAKE_DNS_NETWORK = ipaddress.ip_network("198.18.0.0/15")


class KubeEndpointError(ValueError):
    pass


@dataclass(frozen=True)
class EndpointRewrite:
    server: str
    tls_server_name: str


def choose_endpoint_rewrite(
    server: str, resolved_addresses: list[str], provider_ip: str
) -> EndpointRewrite | None:
    parsed = urlsplit(server)
    if parsed.scheme != "https" or not parsed.hostname:
        raise KubeEndpointError("Kubernetes API server must be an HTTPS hostname")
    if not resolved_addresses:
        raise KubeEndpointError("Kubernetes API hostname did not resolve")
    resolved = [ipaddress.ip_address(value) for value in resolved_addresses]
    if not all(address in FAKE_DNS_NETWORK for address in resolved):
        return None
    target = ipaddress.ip_address(provider_ip)
    if target.version != 4 or not target.is_global or target in FAKE_DNS_NETWORK:
        raise KubeEndpointError(
            "Provider Kubernetes API IP is not a public IPv4 address"
        )
    port = parsed.port or 443
    return EndpointRewrite(
        server=f"https://{target}:{port}",
        tls_server_name=parsed.hostname,
    )


def _kubectl_view(kubeconfig: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "kubectl",
            "--kubeconfig",
            str(kubeconfig),
            "config",
            "view",
            "--minify",
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def repair_fake_dns_endpoint(kubeconfig: Path, provider_ip: str) -> str:
    view = _kubectl_view(kubeconfig)
    clusters = view.get("clusters")
    if not isinstance(clusters, list) or len(clusters) != 1:
        raise KubeEndpointError("Kubeconfig must contain one active cluster")
    cluster_record = clusters[0]
    cluster_name = cluster_record.get("name")
    cluster = cluster_record.get("cluster")
    if not isinstance(cluster_name, str) or not isinstance(cluster, dict):
        raise KubeEndpointError("Kubeconfig cluster identity is incomplete")
    server = cluster.get("server")
    if not isinstance(server, str):
        raise KubeEndpointError("Kubeconfig server is absent")
    host = urlsplit(server).hostname
    if not host:
        raise KubeEndpointError("Kubeconfig server hostname is absent")
    resolved = sorted(
        {item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    )
    rewrite = choose_endpoint_rewrite(server, resolved, provider_ip)
    if rewrite is None:
        return "DNS"
    subprocess.run(
        [
            "kubectl",
            "--kubeconfig",
            str(kubeconfig),
            "config",
            "set-cluster",
            cluster_name,
            f"--server={rewrite.server}",
            f"--tls-server-name={rewrite.tls_server_name}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return "PROVIDER_IP_TLS_NAME_PRESERVED"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kubeconfig", type=Path, required=True)
    parser.add_argument("--provider-ip", required=True)
    args = parser.parse_args()
    mode = repair_fake_dns_endpoint(args.kubeconfig.resolve(), args.provider_ip)
    print(f"KUBE_ENDPOINT={mode}")


if __name__ == "__main__":
    main()
