# RM-002 Java Business Service Gate Evidence

Date: 2026-08-21 Asia/Shanghai

Revision: Worktree based on `ca6df8a`; the exact RM-002 checkpoint is the commit
containing this evidence file.

## Runtime and build

The repository Maven Wrapper uses Maven 3.9.16. `scripts/business-api.ps1`
discovers the active JDK from `PATH`, validates that it includes `javac`, and sets
`JAVA_HOME` for the child process. This prevented a stale machine-level JDK 8
setting from silently controlling the build.

```text
Java: 17.0.1
Spring Boot: 4.1.1
scripts/business-api.ps1 test
PASS: 7 tests, 0 failures, 0 errors

scripts/business-api.ps1 package
PASS: executable Spring Boot JAR produced

scripts/full-gate.ps1 -Infrastructure
PASS: control-plane, Compose, live infrastructure health, and Java gates
```

The test gate performs a clean build so deleted test resources cannot remain on
the incremental classpath. Coverage includes domain invariants, three ArchUnit
layer rules, application startup, health and system HTTP responses, and Flyway
schema history.

## Real PostgreSQL and HTTP gate

The Compose baseline was started and all PostgreSQL, RabbitMQ, and Redis health
checks passed. The unprofiled service then connected to the real PostgreSQL
container and applied `V1__baseline.sql`.

```text
GET http://127.0.0.1:18080/actuator/health
PASS: status=UP

GET http://127.0.0.1:18080/api/v1/system
PASS: service=business-api, runtime=java, architectureVersion=v1

SELECT version || ':' || success
FROM routemind.flyway_schema_history;
PASS: 1:true
```

PostgreSQL reported version 18.6 and Hibernate reported the default schema as
`routemind/routemind`. The application completed graceful Tomcat, JPA, and Hikari
shutdown. Compose containers and the project network were then removed while the
named development volumes were preserved.

## Defects caught during validation

- ArchUnit initially imported test classes and treated test-library imports as
  domain dependencies. Production-only import is now explicit and shared.
- A deleted test `application.yml` remained in Maven's incremental output and
  shadowed the main configuration. Repository test/package commands now begin
  with `clean`, and test configuration uses an explicit `test` profile.
- PowerShell expanded a single Maven goal as individual characters in the first
  wrapper implementation. Commands now pass explicit Maven argument tokens.
