from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from disaster_recovery import LOCAL_CLASSIFICATION, REQUIRED_CHECKS, canonical_digest, validate_report
from recovery_contract import RecoveryArtifact, RecoveryPackage, RollbackManifest, rehearse, sha256_file

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "services" / "business-api" / "src" / "main" / "resources" / "db" / "migration"
POSTGRES_IMAGE = os.environ.get("POSTGRES_IMAGE", "postgres:18.6-alpine")
RABBITMQ_IMAGE = os.environ.get("RABBITMQ_IMAGE", "rabbitmq:4.3.5-management-alpine")
REDIS_IMAGE = os.environ.get("REDIS_IMAGE", "redis:8.10.1-alpine")
TENANTS = ("11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222")


class DrillFailure(RuntimeError):
    pass


def run(arguments: list[str], *, input_bytes: bytes | None = None, check: bool = True) -> bytes:
    result = subprocess.run(arguments, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise DrillFailure(f"command failed ({result.returncode}): {' '.join(arguments)}\n{stderr}")
    return result.stdout


def docker(*arguments: str, input_bytes: bytes | None = None, check: bool = True) -> bytes:
    return run(["docker", *arguments], input_bytes=input_bytes, check=check)


def command_succeeds(arguments: list[str]) -> bool:
    result = subprocess.run(arguments, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def remove_container(name: str) -> None:
    inspected = docker("inspect", name, check=False)
    if inspected:
        docker("rm", "-f", "-v", name, check=False)


def wait_until(label: str, probe, timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "not ready"
    while time.monotonic() < deadline:
        try:
            if probe():
                return
        except (DrillFailure, OSError, urllib.error.URLError) as error:
            last_error = str(error)
        time.sleep(1)
    raise DrillFailure(f"{label} did not become ready: {last_error}")


def start_postgres(name: str, password: str) -> None:
    docker(
        "run",
        "-d",
        "--name",
        name,
        "-e",
        "POSTGRES_DB=routemind",
        "-e",
        "POSTGRES_USER=routemind",
        "-e",
        f"POSTGRES_PASSWORD={password}",
        POSTGRES_IMAGE,
    )
    wait_until(
        name,
        lambda: docker("exec", name, "pg_isready", "-U", "routemind", "-d", "routemind", check=False).strip().endswith(b"accepting connections"),
    )


def psql(name: str, sql: str) -> str:
    output = docker(
        "exec",
        "-i",
        name,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        "routemind",
        "-d",
        "routemind",
        "-At",
        input_bytes=sql.encode("utf-8"),
    )
    return output.decode("utf-8").strip()


def apply_migrations(name: str) -> None:
    files = sorted(MIGRATIONS.glob("V*__*.sql"), key=lambda path: int(re.match(r"V(\d+)__", path.name).group(1)))  # type: ignore[union-attr]
    for path in files:
        psql(name, path.read_text(encoding="utf-8"))


def seed_postgres(name: str) -> None:
    statements: list[str] = []
    for index, tenant in enumerate(TENANTS, start=1):
        order_id = f"{index:08d}-0000-4000-8000-000000000001"
        event_id = f"{index:08d}-0000-4000-8000-000000000002"
        inbox_id = f"{index:08d}-0000-4000-8000-000000000003"
        courier_id = f"{index:08d}-0000-4000-8000-000000000004"
        reconciliation_id = f"{index:08d}-0000-4000-8000-000000000005"
        correlation_id = f"{index:08d}-0000-4000-8000-000000000006"
        payload = json.dumps({"tenantId": tenant, "orderId": order_id}, separators=(",", ":"))
        report_json = json.dumps({"status": "HEALTHY", "tenantId": tenant}, separators=(",", ":"))
        report_digest = hashlib.sha256(report_json.encode("utf-8")).hexdigest()
        statements.extend(
            [
                f"INSERT INTO routemind.orders (id,status,created_at,updated_at,version,tenant_id) VALUES ('{order_id}','CREATED','2026-08-25T00:00:0{index}Z','2026-08-25T00:00:0{index}Z',1,'{tenant}');",
                f"INSERT INTO routemind.order_transitions (order_id,sequence_number,from_status,to_status,actor,occurred_at,tenant_id) VALUES ('{order_id}',1,'CREATED','CONFIRMED','r4-406-drill','2026-08-25T00:01:0{index}Z','{tenant}');",
                f"INSERT INTO routemind.outbox_messages (event_id,event_type,occurred_at,producer,aggregate_id,aggregate_version,correlation_id,trace_id,payload_json,status,attempts,next_attempt_at,created_at,published_at,tenant_id) VALUES ('{event_id}','order.created','2026-08-25T00:00:0{index}Z','business-api','{order_id}',1,'{correlation_id}','{index:032x}',\u0024payload\u0024{payload}\u0024payload\u0024,'PUBLISHED',1,'2026-08-25T00:00:0{index}Z','2026-08-25T00:00:0{index}Z','2026-08-25T00:00:0{index}Z','{tenant}');",
                f"INSERT INTO routemind.inbox_messages (event_id,event_type,occurred_at,producer,aggregate_id,aggregate_version,correlation_id,trace_id,payload_json,status,attempts,next_attempt_at,received_at,processed_at,tenant_id) VALUES ('{inbox_id}','dispatch.completed','2026-08-25T00:02:0{index}Z','compute-api','{order_id}',1,'{correlation_id}','{index:032x}',\u0024payload\u0024{payload}\u0024payload\u0024,'PROCESSED',1,'2026-08-25T00:02:0{index}Z','2026-08-25T00:02:0{index}Z','2026-08-25T00:02:0{index}Z','{tenant}');",
                f"INSERT INTO routemind.courier_locations (courier_id,latitude,longitude,observed_at,tenant_id) VALUES ('{courier_id}',35.68{index},139.76{index},'2026-08-25T00:03:0{index}Z','{tenant}');",
                f"INSERT INTO routemind.reconciliation_runs (run_id,checked_at,status,repair_mode,violation_count,unavailable_count,report_digest,report_json,tenant_id) VALUES ('{reconciliation_id}','2026-08-25T00:04:0{index}Z','HEALTHY','DETECT_ONLY',0,0,'{report_digest}',\u0024report\u0024{report_json}\u0024report\u0024,'{tenant}');",
            ]
        )
    psql(name, "\n".join(statements))


def postgres_snapshot(name: str) -> dict[str, Any]:
    queries = {
        "orders": "SELECT count(*) FROM routemind.orders;",
        "transitions": "SELECT count(*) FROM routemind.order_transitions;",
        "outbox": "SELECT count(*) FROM routemind.outbox_messages;",
        "inbox": "SELECT count(*) FROM routemind.inbox_messages;",
        "locations": "SELECT count(*) FROM routemind.courier_locations;",
        "reconciliation": "SELECT count(*) FROM routemind.reconciliation_runs WHERE repair_mode='DETECT_ONLY';",
        "tenants": "SELECT count(DISTINCT tenant_id) FROM routemind.orders;",
        "rows": "SELECT string_agg(tenant_id::text||':'||id::text||':'||status,'|' ORDER BY tenant_id,id) FROM routemind.orders;",
        "audit": "SELECT string_agg(tenant_id::text||':'||order_id::text||':'||sequence_number::text||':'||actor,'|' ORDER BY tenant_id,order_id) FROM routemind.order_transitions;",
        "event_ids": "SELECT string_agg(tenant_id::text||':'||event_id::text,'|' ORDER BY tenant_id,event_id) FROM routemind.outbox_messages;",
        "inbox_ids": "SELECT string_agg(tenant_id::text||':'||event_id::text,'|' ORDER BY tenant_id,event_id) FROM routemind.inbox_messages;",
    }
    values = {key: psql(name, query) for key, query in queries.items()}
    for key in ("orders", "transitions", "outbox", "inbox", "locations", "reconciliation", "tenants"):
        values[key] = int(values[key])
    values["digest"] = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return values


def dump_postgres(name: str, path: Path) -> None:
    payload = docker("exec", name, "pg_dump", "-U", "routemind", "-d", "routemind", "--format=custom", "--no-owner", "--no-privileges")
    path.write_bytes(payload)


def restore_postgres(name: str, path: Path) -> None:
    docker(
        "exec",
        "-i",
        name,
        "pg_restore",
        "-U",
        "routemind",
        "-d",
        "routemind",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        input_bytes=path.read_bytes(),
    )


def start_rabbit(name: str, password: str) -> None:
    docker(
        "run",
        "-d",
        "--name",
        name,
        "-P",
        "-e",
        "RABBITMQ_DEFAULT_USER=routemind",
        "-e",
        f"RABBITMQ_DEFAULT_PASS={password}",
        RABBITMQ_IMAGE,
    )
    try:
        wait_until(name, lambda: command_succeeds(["docker", "exec", name, "rabbitmq-diagnostics", "-q", "ping"]))
    except DrillFailure as error:
        logs = docker("logs", "--tail", "100", name, check=False).decode("utf-8", errors="replace")
        raise DrillFailure(f"{error}\nRabbitMQ container logs:\n{logs}") from error


def rabbit_port(name: str) -> int:
    output = docker("port", name, "15672/tcp").decode("utf-8")
    matches = re.findall(r":(\d+)\s*$", output, flags=re.MULTILINE)
    if not matches:
        raise DrillFailure("RabbitMQ management port was not published")
    return int(matches[0])


def rabbit_request(port: int, password: str, method: str, path: str, payload: object | None = None) -> Any:
    token = base64.b64encode(f"routemind:{password}".encode("utf-8")).decode("ascii")
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read()
        return json.loads(body) if body else None


def wait_rabbit_http(port: int, password: str) -> None:
    wait_until("RabbitMQ management API", lambda: bool(rabbit_request(port, password, "GET", "/api/overview")))


def configure_rabbit(port: int, password: str, vhost: str) -> None:
    encoded_vhost = urllib.parse.quote(vhost, safe="")
    rabbit_request(port, password, "PUT", f"/api/vhosts/{encoded_vhost}", {})
    rabbit_request(port, password, "PUT", f"/api/permissions/{encoded_vhost}/routemind", {"configure": ".*", "write": ".*", "read": ".*"})
    rabbit_request(port, password, "PUT", f"/api/exchanges/{encoded_vhost}/routemind.events", {"type": "topic", "durable": True, "auto_delete": False, "arguments": {}})
    rabbit_request(port, password, "PUT", f"/api/queues/{encoded_vhost}/routemind.orders", {"durable": True, "auto_delete": False, "arguments": {}})
    rabbit_request(port, password, "POST", f"/api/bindings/{encoded_vhost}/e/routemind.events/q/routemind.orders", {"routing_key": "order.events", "arguments": {}})


def export_rabbit(port: int, password: str, vhost: str, path: Path) -> None:
    encoded_vhost = urllib.parse.quote(vhost, safe="")
    definitions = rabbit_request(port, password, "GET", f"/api/definitions/{encoded_vhost}")
    payload = json.dumps(definitions, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if b"password" in payload.lower():
        raise DrillFailure("vhost definitions unexpectedly contain credential material")
    path.write_bytes(payload)


def import_rabbit(port: int, password: str, vhost: str, path: Path) -> None:
    encoded_vhost = urllib.parse.quote(vhost, safe="")
    rabbit_request(port, password, "PUT", f"/api/vhosts/{encoded_vhost}", {})
    rabbit_request(port, password, "PUT", f"/api/permissions/{encoded_vhost}/routemind", {"configure": ".*", "write": ".*", "read": ".*"})
    rabbit_request(port, password, "POST", f"/api/definitions/{encoded_vhost}", json.loads(path.read_text(encoding="utf-8")))


def verify_and_replay_rabbit(port: int, password: str, vhost: str, count: int) -> None:
    encoded_vhost = urllib.parse.quote(vhost, safe="")
    queue = rabbit_request(port, password, "GET", f"/api/queues/{encoded_vhost}/routemind.orders")
    if queue.get("durable") is not True:
        raise DrillFailure("RabbitMQ durable topology was not restored")
    for index in range(count):
        result = rabbit_request(
            port,
            password,
            "POST",
            f"/api/exchanges/{encoded_vhost}/routemind.events/publish",
            {"properties": {"message_id": f"replay-{index}"}, "routing_key": "order.events", "payload": json.dumps({"replay": index}), "payload_encoding": "string"},
        )
        if result.get("routed") is not True:
            raise DrillFailure("Outbox replay was not routed")

    def messages_ready() -> bool:
        current = rabbit_request(port, password, "GET", f"/api/queues/{encoded_vhost}/routemind.orders")
        return current.get("messages_ready") == count

    wait_until("RabbitMQ replay messages", messages_ready, timeout_seconds=30)


def start_redis(name: str, password: str, *, create_only: bool = False) -> None:
    verb = "create" if create_only else "run"
    arguments = [verb]
    if not create_only:
        arguments.append("-d")
    arguments.extend(["--name", name, REDIS_IMAGE, "redis-server", "--requirepass", password, "--save", "60", "1"])
    docker(*arguments)
    if not create_only:
        wait_redis(name, password)


def wait_redis(name: str, password: str) -> None:
    wait_until(name, lambda: docker("exec", name, "redis-cli", "-a", password, "--no-auth-warning", "PING", check=False).strip() == b"PONG")


def redis(name: str, password: str, *arguments: str) -> str:
    return docker("exec", name, "redis-cli", "-a", password, "--no-auth-warning", *arguments).decode("utf-8").strip()


def seed_redis(name: str, password: str) -> None:
    for index, tenant in enumerate(TENANTS, start=1):
        courier_id = f"{index:08d}-0000-4000-8000-000000000004"
        key = f"routemind:couriers:{tenant}"
        if redis(name, password, "GEOADD", key, f"139.76{index}", f"35.68{index}", courier_id) != "1":
            raise DrillFailure("Redis GEO fixture was not created")
    redis(name, password, "SET", "r4-406:fixture", "committed")


def dump_redis(name: str, password: str, path: Path) -> None:
    if redis(name, password, "SAVE") != "OK":
        raise DrillFailure("Redis SAVE failed")
    docker("cp", f"{name}:/data/dump.rdb", str(path))


def restore_redis(name: str, password: str, path: Path) -> None:
    start_redis(name, password, create_only=True)
    docker("cp", str(path), f"{name}:/data/dump.rdb")
    docker("start", name)
    wait_redis(name, password)


def verify_and_rebuild_redis(name: str, password: str, postgres_name: str) -> None:
    for tenant in TENANTS:
        if redis(name, password, "ZCARD", f"routemind:couriers:{tenant}") != "1":
            raise DrillFailure("Redis snapshot GEO projection was not restored")
    lost_tenant = TENANTS[1]
    redis(name, password, "DEL", f"routemind:couriers:{lost_tenant}")
    rows = psql(
        postgres_name,
        f"SELECT tenant_id||'|'||courier_id||'|'||longitude||'|'||latitude FROM routemind.courier_locations WHERE tenant_id='{lost_tenant}' ORDER BY courier_id;",
    ).splitlines()
    for row in rows:
        tenant, courier_id, longitude, latitude = row.split("|")
        redis(name, password, "GEOADD", f"routemind:couriers:{tenant}", longitude, latitude, courier_id)
    if redis(name, password, "ZCARD", f"routemind:couriers:{lost_tenant}") != "1":
        raise DrillFailure("Redis projection rebuild from PostgreSQL failed")


def artifact(service: str, format_name: str, path: Path, order: int, revision: str) -> RecoveryArtifact:
    return RecoveryArtifact(
        f"r4-406-{service}",
        service,  # type: ignore[arg-type]
        format_name,  # type: ignore[arg-type]
        revision,
        path.name,
        sha256_file(path),
        path.stat().st_size,
        order,
        (("scope", "isolated-fixture"),),
    )


def execute(output: Path) -> dict[str, Any]:
    run_id = uuid.uuid4().hex[:12]
    prefix = f"r4-406-{run_id}"
    names = {
        "pg_source": f"{prefix}-pg-source",
        "rabbit_source": f"{prefix}-rabbit-source",
        "redis_source": f"{prefix}-redis-source",
        "pg_restore": f"{prefix}-pg-restore",
        "rabbit_restore": f"{prefix}-rabbit-restore",
        "redis_restore": f"{prefix}-redis-restore",
        "pg_rollback": f"{prefix}-pg-rollback",
    }
    postgres_password = secrets.token_urlsafe(24)
    rabbit_password = secrets.token_urlsafe(24)
    redis_password = secrets.token_urlsafe(24)
    revision = run(["git", "rev-parse", "HEAD"]).decode("ascii").strip()
    started_at = datetime.now(UTC)
    checks = {name: False for name in REQUIRED_CHECKS}

    with tempfile.TemporaryDirectory(prefix="r4-406-") as directory:
        package_root = Path(directory)
        postgres_dump = package_root / "postgres.dump"
        rabbit_definitions = package_root / "rabbitmq-definitions.json"
        redis_dump = package_root / "redis.rdb"
        try:
            start_postgres(names["pg_source"], postgres_password)
            apply_migrations(names["pg_source"])
            seed_postgres(names["pg_source"])
            source = postgres_snapshot(names["pg_source"])
            if any(source[key] != 2 for key in ("orders", "transitions", "outbox", "inbox", "locations", "reconciliation", "tenants")):
                raise DrillFailure(f"PostgreSQL source fixture is incomplete: {source}")
            dump_postgres(names["pg_source"], postgres_dump)

            vhost = "/r4-406"
            start_rabbit(names["rabbit_source"], rabbit_password)
            source_rabbit_port = rabbit_port(names["rabbit_source"])
            wait_rabbit_http(source_rabbit_port, rabbit_password)
            configure_rabbit(source_rabbit_port, rabbit_password, vhost)
            export_rabbit(source_rabbit_port, rabbit_password, vhost, rabbit_definitions)

            start_redis(names["redis_source"], redis_password)
            seed_redis(names["redis_source"], redis_password)
            dump_redis(names["redis_source"], redis_password, redis_dump)

            package = RecoveryPackage(
                f"r4-406-{run_id}",
                started_at.isoformat().replace("+00:00", "Z"),
                revision,
                (
                    artifact("postgres", "pg_dump", postgres_dump, 1, revision),
                    artifact("rabbitmq", "rabbitmq-definitions", rabbit_definitions, 2, revision),
                    artifact("redis", "redis-rdb", redis_dump, 3, revision),
                ),
                (("environment", "local-ci"), ("production-data", "false")),
            )
            rehearsal = rehearse(package, package_root)
            if rehearsal.status != "ready":
                raise DrillFailure(f"Recovery package validation failed: {rehearsal.reasons}")

            for source_name in (names["pg_source"], names["rabbit_source"], names["redis_source"]):
                remove_container(source_name)

            restore_started = time.monotonic()
            start_postgres(names["pg_restore"], postgres_password)
            restore_postgres(names["pg_restore"], postgres_dump)
            restored = postgres_snapshot(names["pg_restore"])
            if restored["digest"] != source["digest"]:
                raise DrillFailure("PostgreSQL restored digest differs from source")
            checks.update(
                postgres_restore=True,
                tenant_isolation=restored["tenants"] == 2,
                audit_continuity=restored["transitions"] == source["transitions"] and restored["audit"] == source["audit"],
                outbox_restore=restored["outbox"] == source["outbox"] and restored["event_ids"] == source["event_ids"],
                inbox_restore=restored["inbox"] == source["inbox"] and restored["inbox_ids"] == source["inbox_ids"],
                reconciliation_evidence=restored["reconciliation"] == source["reconciliation"],
            )

            start_rabbit(names["rabbit_restore"], rabbit_password)
            restored_rabbit_port = rabbit_port(names["rabbit_restore"])
            wait_rabbit_http(restored_rabbit_port, rabbit_password)
            import_rabbit(restored_rabbit_port, rabbit_password, vhost, rabbit_definitions)
            verify_and_replay_rabbit(restored_rabbit_port, rabbit_password, vhost, restored["outbox"])
            checks["rabbitmq_topology_restore"] = True
            checks["outbox_replay"] = True

            restore_redis(names["redis_restore"], redis_password, redis_dump)
            for tenant in TENANTS:
                if redis(names["redis_restore"], redis_password, "ZCARD", f"routemind:couriers:{tenant}") != "1":
                    raise DrillFailure("Redis snapshot check failed")
            checks["redis_snapshot_restore"] = True
            verify_and_rebuild_redis(names["redis_restore"], redis_password, names["pg_restore"])
            checks["redis_projection_rebuild"] = True
            rto_seconds = round(time.monotonic() - restore_started, 3)

            rollback_manifest = RollbackManifest(
                f"r4-406-rollback-{run_id}",
                revision,
                package.digest,
                "ci-operator",
                "restore last checksum-verified package after isolated mutation",
                (("ack", "required"), ("scope", "isolated-ephemeral")),
            )
            psql(names["pg_restore"], "DELETE FROM routemind.order_transitions WHERE tenant_id='22222222-2222-4222-8222-222222222222';")
            if postgres_snapshot(names["pg_restore"])["digest"] == source["digest"]:
                raise DrillFailure("rollback precondition mutation did not change the digest")
            rollback_started = time.monotonic()
            remove_container(names["pg_restore"])
            start_postgres(names["pg_rollback"], postgres_password)
            restore_postgres(names["pg_rollback"], postgres_dump)
            rollback = postgres_snapshot(names["pg_rollback"])
            rollback_seconds = round(time.monotonic() - rollback_started, 3)
            if rollback["digest"] != source["digest"]:
                raise DrillFailure("rollback restore digest differs from source")
            checks["rollback_restore"] = True

            if set(checks) != REQUIRED_CHECKS or not all(checks.values()):
                raise DrillFailure(f"required recovery checks did not all pass: {checks}")
            artifacts = [
                {"service": item.service, "format": item.format, "sha256": item.sha256, "byteSize": item.byte_size}
                for item in package.artifacts
            ]
            report: dict[str, Any] = {
                "schemaVersion": "r4-406.v1",
                "reportId": f"r4-406-{run_id}",
                "sourceRevision": revision,
                "startedAt": started_at.isoformat().replace("+00:00", "Z"),
                "completedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "classification": LOCAL_CLASSIFICATION,
                "productionDeploymentVerified": False,
                "environment": {"mode": "local-ci", "provider": "Docker", "region": "loopback", "targetEvidenceSha256": None},
                "safety": {"scope": "isolated_ephemeral_only", "productionDataUsed": False, "sourceContainersDestroyedBeforeRestore": True},
                "artifacts": artifacts,
                "packageDigest": package.digest,
                "checks": dict(sorted(checks.items())),
                "metrics": {"rpoSeconds": 0, "rtoSeconds": rto_seconds, "rollbackSeconds": rollback_seconds},
                "continuity": {"tenantCount": source["tenants"], "sourceDigest": source["digest"], "restoredDigest": restored["digest"], "rollbackDigest": rollback["digest"]},
                "rollback": {"ack": "required", "manifestDigest": rollback_manifest.digest},
                "limitations": [
                    "ephemeral Docker evidence is not Vultr Tokyo target evidence",
                    "zero fixture data loss is not a production RPO claim",
                    "measured local restore time is not a production RTO claim",
                ],
            }
            report["reportDigest"] = canonical_digest(report)
            findings = validate_report(report)
            if findings:
                raise DrillFailure(f"generated report is invalid: {findings}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return report
        finally:
            for name in names.values():
                remove_container(name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated R4-406 recovery drill")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "tests" / "tmp" / "R4-406" / "local-drill.json")
    arguments = parser.parse_args()
    if not shutil_which("docker"):
        raise DrillFailure("Docker CLI is required")
    docker("version", "--format", "{{.Server.Version}}")
    report = execute(arguments.output.resolve())
    print(json.dumps({"classification": report["classification"], "reportDigest": report["reportDigest"], "rpoSeconds": report["metrics"]["rpoSeconds"], "rtoSeconds": report["metrics"]["rtoSeconds"], "valid": True}, sort_keys=True))
    return 0


def shutil_which(command: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() or (os.name == "nt" and candidate.with_suffix(".exe").is_file()):
            return str(candidate)
    return None


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (DrillFailure, OSError, urllib.error.URLError) as error:
        print(f"R4-406 recovery drill failed: {error}", file=sys.stderr)
        sys.exit(1)
