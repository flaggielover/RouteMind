# R4 Edge Security and Supply-Chain Policy

## Request boundary

`edge-v1` runs inside the Java Spring Security chain after tenant and actor
identity have been established. Its fixed-window key is a SHA-256 digest of the
verified tenant, role quota, authenticated subject (or anonymous peer), method,
and normalized route template. UUID and numeric path segments normalize to an
identity-free placeholder, so counters do not leak aggregate IDs or create an
unbounded key per resource.

The role ceilings are explicit configuration. A principal with multiple known
roles receives the largest verified-role ceiling; an unknown authenticated role
uses the authenticated baseline. The policy never trusts a role or tenant from a
caller-controlled header. A bounded in-process counter is the current per-instance
primary adapter. A separately allocated bounded counter is used when the primary
fails; if both fail, protected traffic fails closed with `503`. Exhausted quotas
return `429`, deterministic `Retry-After`, and non-sensitive limit metadata.

This is not a claim of fleet-wide or production quota enforcement. A deployed
multi-replica gateway must bind the same key and policy version to an approved
atomic shared limiter before a fleet-wide rate claim is admissible.

## Local WAF-equivalent policy

The filter rejects unsupported methods, path traversal encodings, control
characters, ambiguous `Host` or `Content-Length`, simultaneous transfer encoding
and content length, excessive path/query/header/body measurements, and body-bearing
JSON commands without an application/json content type. It evaluates request
structure only. Authentication, authorization, tenant isolation, transactions,
and durable command correctness remain Java-owned application boundaries.

Commands without a declared content length are not treated as unlimited. Their
stream is captured once into a configured bounded buffer and replayed downstream;
the filter returns `413` as soon as one byte beyond the limit is observed. The
configured body ceiling must fit in a Java array and invalid values fail during
configuration binding.

This executable policy is the task's WAF-equivalent evidence. No managed WAF,
bot-reputation provider, credential-reputation feed, penetration test, or vendor
deployment is claimed.

## Supply-chain evidence

`scripts/supply-chain.ps1` resolves the Maven dependency tree and combines it
with exact `uv.lock` and npm lockfile data into a CycloneDX 1.6 SBOM. In CI it
also resolves the current OCI registry manifest for every Compose image. The
generator writes a content-addressed in-toto Statement v1 with an SLSA provenance
predicate binding the source revision, dependency inputs, SBOM, and registry
manifest payloads. The Java CI job validates and retains the bundle for 30 days.

The statement deliberately records `signed=false`. It is reproducible CI
provenance and dependency attestation evidence, not a cryptographic signature,
GitHub artifact attestation, registry signature, vulnerability scan, or guarantee
that an image tag will remain immutable. Production signing and registry policy
remain deployment-target work behind their own approval and external gates.
