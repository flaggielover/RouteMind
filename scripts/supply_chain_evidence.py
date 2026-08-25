from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
JAVA_COORDINATE = re.compile(
    r"(?P<group>[A-Za-z0-9_.-]+):(?P<name>[A-Za-z0-9_.-]+):"
    r"(?P<type>[A-Za-z0-9_.-]+):(?:(?P<classifier>[A-Za-z0-9_.-]+):)?"
    r"(?P<version>[A-Za-z0-9_.+\-]+):(?P<scope>[A-Za-z0-9_.-]+)"
)
IMAGE_EXPRESSION = re.compile(r"^\$\{[A-Z0-9_]+:-(?P<default>[^}]+)}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ContainerReference:
    service: str
    image: str


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def compose_images(path: Path) -> tuple[ContainerReference, ...]:
    services = False
    current: str | None = None
    found: list[ContainerReference] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "services:":
            services = True
            continue
        if services and line and not line.startswith(" "):
            services = False
        service = re.fullmatch(r"  ([a-z0-9][a-z0-9_-]*):", line)
        if services and service:
            current = service.group(1)
            continue
        image = re.fullmatch(r"    image:\s+(.+)", line)
        if services and current and image:
            value = image.group(1).strip().strip('"\'')
            expression = IMAGE_EXPRESSION.fullmatch(value)
            found.append(ContainerReference(current, expression.group("default") if expression else value))
    if not found or len({item.service for item in found}) != len(found):
        raise ValueError("compose image references must be present and unique by service")
    return tuple(found)


def java_components(path: Path) -> list[dict[str, Any]]:
    components: dict[str, dict[str, Any]] = {}
    for match in JAVA_COORDINATE.finditer(path.read_text(encoding="utf-8")):
        group, name, version = match.group("group", "name", "version")
        if group == "com.routemind" and name == "business-api":
            continue
        ref = f"pkg:maven/{quote(group, safe='.')}/{quote(name)}@{quote(version)}"
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": ref,
            "group": group,
            "name": name,
            "version": version,
            "purl": ref,
            "properties": [{"name": "routemind.scope", "value": match.group("scope")}],
        }
        components[ref] = component
    if not components:
        raise ValueError("resolved Maven dependency tree contains no components")
    return list(components.values())


def python_components(path: Path) -> list[dict[str, Any]]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    components: list[dict[str, Any]] = []
    for package in payload.get("package", []):
        name = str(package["name"])
        version = str(package["version"])
        ref = f"pkg:pypi/{quote(name)}@{quote(version)}"
        hashes: set[str] = set()
        candidates = [package.get("sdist"), *package.get("wheels", [])]
        for candidate in candidates:
            if isinstance(candidate, dict) and str(candidate.get("hash", "")).startswith("sha256:"):
                value = str(candidate["hash"]).removeprefix("sha256:")
                if SHA256.fullmatch(value):
                    hashes.add(value.upper())
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": version,
            "purl": ref,
        }
        if hashes:
            component["hashes"] = [{"alg": "SHA-256", "content": value} for value in sorted(hashes)]
        components.append(component)
    if not components:
        raise ValueError("uv lock contains no packages")
    return components


def npm_components(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    components: dict[str, dict[str, Any]] = {}
    for package_path, package in payload.get("packages", {}).items():
        if not package_path or "version" not in package:
            continue
        marker = "node_modules/"
        name = str(package.get("name") or package_path.rsplit(marker, 1)[-1])
        version = str(package["version"])
        if name.startswith("@") and "/" in name:
            namespace, package_name = name.split("/", 1)
            purl_name = f"{quote(namespace, safe='')}/{quote(package_name, safe='')}"
        else:
            purl_name = quote(name, safe="")
        ref = f"pkg:npm/{purl_name}@{quote(version, safe='')}"
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": version,
            "purl": ref,
            "properties": [
                {"name": "routemind.development", "value": str(bool(package.get("dev"))).lower()}
            ],
        }
        integrity = str(package.get("integrity", ""))
        if integrity.startswith("sha512-"):
            component["properties"].append(
                {"name": "routemind.npm.integrity", "value": integrity}
            )
        components[ref] = component
    if not components:
        raise ValueError("npm lock contains no packages")
    return list(components.values())


def container_components(
    references: tuple[ContainerReference, ...], manifest_dir: Path, require_manifests: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    components: list[dict[str, Any]] = []
    subjects: list[dict[str, Any]] = []
    for reference in references:
        manifest_path = manifest_dir / f"{reference.service}.manifest.json"
        if not manifest_path.is_file():
            if require_manifests:
                raise ValueError(f"OCI registry manifest missing for {reference.service}")
            continue
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
        manifest_digest = digest_bytes(raw)
        descriptors = manifest.get("manifests", [])
        registry_digests = sorted(
            str(item["digest"])
            for item in descriptors
            if isinstance(item, dict) and str(item.get("digest", "")).startswith("sha256:")
        )
        config = manifest.get("config")
        if isinstance(config, dict) and str(config.get("digest", "")).startswith("sha256:"):
            registry_digests.append(str(config["digest"]))
        ref = f"pkg:oci/{quote(reference.service)}@{quote(reference.image)}"
        components.append(
            {
                "type": "container",
                "bom-ref": ref,
                "name": reference.service,
                "version": reference.image,
                "purl": ref,
                "hashes": [{"alg": "SHA-256", "content": manifest_digest.upper()}],
                "properties": [
                    {"name": "routemind.oci.reference", "value": reference.image},
                    {"name": "routemind.oci.registryManifest", "value": "resolved"},
                    {"name": "routemind.oci.descriptorDigests", "value": ",".join(registry_digests)},
                ],
            }
        )
        subjects.append(
            {
                "name": f"oci-registry-manifest:{reference.service}:{reference.image}",
                "digest": {"sha256": manifest_digest},
            }
        )
    return components, subjects


def git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def build_bundle(
    root: Path,
    java_tree: Path,
    manifest_dir: Path,
    output_dir: Path,
    require_manifests: bool,
    created_at: str | None = None,
    revision: str | None = None,
) -> dict[str, Any]:
    locks = {
        "maven": java_tree,
        "python": root / "services/compute-api/uv.lock",
        "npm": root / "apps/web/package-lock.json",
        "compose": root / "compose.yaml",
    }
    missing = [name for name, path in locks.items() if not path.is_file()]
    if missing:
        raise ValueError(f"supply-chain inputs missing: {', '.join(missing)}")
    references = compose_images(locks["compose"])
    containers, container_subjects = container_components(references, manifest_dir, require_manifests)
    components = java_components(java_tree) + python_components(locks["python"]) + npm_components(locks["npm"])
    components += containers
    components.sort(key=lambda item: str(item["bom-ref"]))
    revision = revision or git_revision(root)
    created_at = created_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    bom: dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{revision[:8]}-{revision[8:12]}-4{revision[13:16]}-a{revision[17:20]}-{revision[20:32]}",
        "version": 1,
        "metadata": {
            "timestamp": created_at,
            "component": {
                "type": "application",
                "bom-ref": f"pkg:generic/routemind@{revision}",
                "name": "RouteMind",
                "version": revision,
            },
            "properties": [
                {"name": "routemind.source.revision", "value": revision},
                {"name": "routemind.container.manifests.required", "value": str(require_manifests).lower()},
            ],
        },
        "components": components,
    }
    sbom_path = output_dir / "routemind.cdx.json"
    write_json(sbom_path, bom)
    sbom_digest = digest_file(sbom_path)
    materials = [
        {"uri": path.relative_to(root).as_posix(), "digest": {"sha256": digest_file(path)}}
        for name, path in locks.items()
        if name != "maven"
    ]
    materials.append({"uri": "resolved-maven-dependency-tree", "digest": {"sha256": digest_file(java_tree)}})
    invocation_id = os.environ.get("GITHUB_RUN_ID", "local")
    statement: dict[str, Any] = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": "routemind.cdx.json", "digest": {"sha256": sbom_digest}},
            *container_subjects,
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://routemind.local/build-types/supply-chain-evidence/v1",
                "externalParameters": {"sourceRevision": revision},
                "internalParameters": {
                    "dependencySources": ["maven-resolved-tree", "uv-lock", "npm-lock-v3"],
                    "containerManifestSource": "OCI registry",
                },
                "resolvedDependencies": materials,
            },
            "runDetails": {
                "builder": {"id": "https://github.com/flaggielover/RouteMind/actions/workflows/ci.yml"},
                "metadata": {"invocationId": invocation_id, "startedOn": created_at, "finishedOn": created_at},
                "byproducts": [{"name": "routemind.cdx.json", "digest": {"sha256": sbom_digest}}],
            },
            "routemind": {
                "signed": False,
                "claimBoundary": "Content-addressed CI evidence; not a cryptographic signature or registry attestation",
            },
        },
    }
    provenance_path = output_dir / "routemind.provenance.intoto.json"
    write_json(provenance_path, statement)
    summary = {
        "schemaVersion": 1,
        "sourceRevision": revision,
        "createdAt": created_at,
        "componentCount": len(components),
        "ecosystemCounts": {
            "maven": len(java_components(java_tree)),
            "pypi": len(python_components(locks["python"])),
            "npm": len(npm_components(locks["npm"])),
            "oci": len(containers),
        },
        "containerReferences": [asdict(reference) for reference in references],
        "containerManifestsResolved": len(containers),
        "sbomSha256": sbom_digest,
        "provenanceSha256": digest_file(provenance_path),
        "signed": False,
    }
    write_json(output_dir / "summary.json", summary)
    validate_bundle(output_dir, len(references) if require_manifests else None)
    return summary


def validate_bundle(output_dir: Path, expected_containers: int | None = None) -> dict[str, Any]:
    sbom_path = output_dir / "routemind.cdx.json"
    provenance_path = output_dir / "routemind.provenance.intoto.json"
    summary_path = output_dir / "summary.json"
    for path in (sbom_path, provenance_path, summary_path):
        if not path.is_file():
            raise ValueError(f"supply-chain output missing: {path.name}")
    bom = json.loads(sbom_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise ValueError("CycloneDX identity mismatch")
    if summary.get("componentCount") != len(bom.get("components", [])):
        raise ValueError("SBOM component count mismatch")
    if summary.get("sbomSha256") != digest_file(sbom_path):
        raise ValueError("SBOM digest mismatch")
    if summary.get("provenanceSha256") != digest_file(provenance_path):
        raise ValueError("provenance digest mismatch")
    subjects = provenance.get("subject", [])
    if not subjects or subjects[0].get("digest", {}).get("sha256") != digest_file(sbom_path):
        raise ValueError("provenance does not bind the SBOM")
    if provenance.get("predicate", {}).get("routemind", {}).get("signed") is not False:
        raise ValueError("unsigned evidence boundary must remain explicit")
    if expected_containers is not None and summary.get("containerManifestsResolved") != expected_containers:
        raise ValueError("not all OCI registry manifests were resolved")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--java-tree", type=Path)
    parser.add_argument("--container-manifest-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--require-container-manifests", action="store_true")
    parser.add_argument("--list-images", action="store_true")
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    try:
        if args.list_images:
            print(json.dumps([asdict(item) for item in compose_images(root / "compose.yaml")]))
            return 0
        if args.validate:
            if args.output_dir is None:
                raise ValueError("--output-dir is required")
            summary = validate_bundle(args.output_dir, len(compose_images(root / "compose.yaml")))
        else:
            if args.java_tree is None or args.container_manifest_dir is None or args.output_dir is None:
                raise ValueError("--java-tree, --container-manifest-dir, and --output-dir are required")
            summary = build_bundle(
                root,
                args.java_tree,
                args.container_manifest_dir,
                args.output_dir,
                args.require_container_manifests,
            )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
