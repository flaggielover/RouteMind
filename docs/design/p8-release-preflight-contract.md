# P8 Release Provenance and Deployment Preflight Contract

## Goal

Make a release candidate auditable before deployment. The preflight contract
binds a source revision to immutable service artifacts, schema migration state,
health checks, and a rollback target. It validates release readiness locally and
does not execute deployment or claim production verification.

## Manifest invariants

`ReleaseManifest` records release ID, source revision, created-at, environment,
service artifact descriptors, contract versions, applied migration heads,
health-check identifiers, and rollback package digest. Artifact descriptors
require service, immutable digest or version, and provenance metadata; `latest`
and blank versions are rejected. Service names and contract keys are unique.

Migration heads are normalized and must be non-empty. A release may only target
an environment explicitly named in the manifest, and rollback metadata must
point at a content digest rather than a mutable tag.

## Preflight

`ReleasePreflight` checks required repository files, manifest consistency,
artifact/version policy, migration heads, health-check coverage, and rollback
linkage. It returns `ready` or `blocked` with stable reason codes and a
content-derived manifest digest. It is read-only and cannot change Compose,
PostgreSQL, RabbitMQ, Redis, or application state.

## Validation boundary

Tests cover deterministic manifest canonicalization, duplicate/missing fields,
mutable tag rejection, migration and health-check coverage, rollback digest
linkage, and stable preflight reason ordering. Live registry signature
verification, image scanning, deployment orchestration, and production health
remain separate external gates.
