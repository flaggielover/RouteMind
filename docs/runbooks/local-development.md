# Local Development Runbook

## Prerequisites

Use PowerShell 7 or Windows PowerShell with Git, Python, Java, Node.js, Docker
Desktop, and the Docker Compose plugin. Java builds use the repository Maven
Wrapper, so a global Maven installation is not required.

The Java command derives `JAVA_HOME` from the active JDK on `PATH`; this avoids a
stale machine-level `JAVA_HOME` selecting a different runtime:

```powershell
./scripts/business-api.ps1 test
```

The Python command installs pinned `uv` into the ignored `.tools` directory and
syncs the compute environment strictly from `uv.lock`:

```powershell
./scripts/compute-api.ps1 check
```

Run:

```powershell
./scripts/bootstrap.ps1
```

The script creates an ignored `.env` from `.env.example` when absent, checks tools
and the external data boundary, then runs the fast repository gate. Change all
placeholder passwords before exposing any service beyond localhost.

## Infrastructure

```powershell
./scripts/infra.ps1 up
./scripts/infra.ps1 status
./scripts/infra.ps1 logs
./scripts/infra.ps1 down
```

`down` preserves the named PostgreSQL, RabbitMQ, and Redis volumes. Intentional
data deletion is not part of the standard script and must use an explicit,
carefully reviewed Docker volume operation.

Default endpoints:

- PostgreSQL: `127.0.0.1:15432`
- RabbitMQ AMQP: `127.0.0.1:15673`
- RabbitMQ Management: `http://127.0.0.1:15674`
- Redis: `127.0.0.1:16379`
- Business API: `http://127.0.0.1:18080`
- Compute API: `http://127.0.0.1:18081`

All published ports bind to loopback. Applications inside the Compose project use
service DNS names (`postgres`, `rabbitmq`, `redis`) and container ports.

## Gates

The fast gate validates Compose without starting containers:

```powershell
./scripts/verify.ps1
```

The infrastructure gate starts dependencies, waits for all health checks, and runs
the available repository gates. It stops containers it started while preserving
volumes, but leaves an already-running development stack running:

```powershell
./scripts/full-gate.ps1 -Infrastructure
```

Pass `-KeepInfrastructure` to leave healthy containers running after the gate.
