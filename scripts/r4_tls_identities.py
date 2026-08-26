from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


class TlsIdentityError(ValueError):
    pass


TLS_IDENTITIES: tuple[dict[str, str], ...] = (
    {
        "name": "signoz",
        "commonName": "routemind-signoz",
        "dnsName": "routemind-signoz-otel-collector.routemind-observability.svc.cluster.local",
        "usage": "serverAuth",
    },
    {
        "name": "receiver",
        "commonName": "routemind-otel-receiver",
        "dnsName": "routemind-otel-collector.routemind-observability.svc.cluster.local",
        "usage": "serverAuth",
    },
    {
        "name": "exporter",
        "commonName": "routemind-collector-client",
        "usage": "clientAuth",
    },
    {
        "name": "probe",
        "commonName": "routemind-validation-probe",
        "usage": "clientAuth",
    },
)


def _validate_dns_name(value: str) -> None:
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise TlsIdentityError("TLS DNS names must be ASCII") from exc
    if not encoded or len(encoded) > 253:
        raise TlsIdentityError("TLS DNS name length is invalid")
    labels = value.rstrip(".").split(".")
    if any(not label or len(label.encode("ascii")) > 63 for label in labels):
        raise TlsIdentityError("TLS DNS label length is invalid")


def validate_identities(
    identities: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    validated: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in identities:
        name = raw.get("name")
        common_name = raw.get("commonName")
        usage = raw.get("usage")
        dns_name = raw.get("dnsName")
        if not isinstance(name, str) or not name or name in seen:
            raise TlsIdentityError("TLS identity name is absent or duplicated")
        if not isinstance(common_name, str) or not common_name:
            raise TlsIdentityError("TLS Common Name is absent")
        if len(common_name.encode("utf-8")) > 64:
            raise TlsIdentityError("TLS Common Name exceeds the X.509 64-byte limit")
        if usage not in {"serverAuth", "clientAuth"}:
            raise TlsIdentityError("TLS extended key usage is invalid")
        identity = {
            "name": name,
            "commonName": common_name,
            "usage": usage,
        }
        if usage == "serverAuth":
            if not isinstance(dns_name, str):
                raise TlsIdentityError("Server TLS identity requires a DNS SAN")
            _validate_dns_name(dns_name)
            identity["dnsName"] = dns_name
        elif dns_name is not None:
            raise TlsIdentityError(
                "Client TLS identity must not declare a server DNS SAN"
            )
        validated.append(identity)
        seen.add(name)
    if seen != {"signoz", "receiver", "exporter", "probe"}:
        raise TlsIdentityError("TLS identity inventory drifted")
    return {"valid": True, "identities": validated}


def main() -> None:
    print(json.dumps(validate_identities(TLS_IDENTITIES), separators=(",", ":")))


if __name__ == "__main__":
    main()
