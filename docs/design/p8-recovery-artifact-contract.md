# P8 Recovery Artifact Contract and Rehearsal Validator

## Goal

Define a portable recovery artifact contract for PostgreSQL, RabbitMQ, and
Redis metadata, then validate a staged recovery package locally without
pretending that a live restore occurred. The contract makes backup identity,
checksums, ordering, service scope, and rollback target explicit.

## Artifact contract

`RecoveryArtifact` is immutable and records an artifact ID, creation time,
source revision, service, format, relative payload path, SHA-256 checksum, byte
size, and optional database/schema or broker/vault metadata. Payload paths must
remain relative to the package root and may not escape it. Services are limited
to `postgres`, `rabbitmq`, and `redis`; formats are explicit (`pg_dump`,
`rabbitmq-definitions`, `redis-rdb`, or `manifest`).

`RecoveryPackage` contains one manifest artifact plus service artifacts. It
rejects duplicate service entries, missing required services, invalid checksums,
unsafe paths, and non-monotonic restore order. Its canonical digest excludes
filesystem timestamps and is reproducible from manifest content.

## Rehearsal and rollback

`RecoveryRehearsal` verifies every payload exists, has the declared size and
checksum, and that the package's restore order is valid. It returns explicit
`ready` or `blocked` status with bounded reason codes. `RollbackManifest`
records the target revision, package digest, operator intent, and a required
confirmation token represented only as metadata; it never performs a state
change. A later deployment task can bind these contracts to vendor-specific
backup/restore commands.

## Evidence boundary

Tests use temporary local fixtures to exercise checksum success/failure,
path traversal rejection, missing service artifacts, deterministic package
digests, restore ordering, and rollback metadata. No production data, external
credentials, destructive volume operation, or live restore claim is made when
Docker or service credentials are unavailable.
