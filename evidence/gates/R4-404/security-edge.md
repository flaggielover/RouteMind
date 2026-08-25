# R4-404 Edge Security and Supply-Chain Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `00c2706bb55abacd089ed83e9fc5a616763b66db`

Status: in progress - `CI_PENDING`

## Implemented boundary

- The versioned Java edge filter runs after verified tenant/actor binding and
  derives an opaque fixed-window key from tenant, verified role quota, subject,
  method, and normalized route. Tenant IDs, subjects, and aggregate IDs are not
  emitted in headers or counter keys.
- Explicit anonymous, authenticated, customer, courier, merchant, analyst, and
  operator ceilings are configurable. Quota exhaustion returns `429` with
  deterministic `Retry-After`; primary-counter failure uses a separate bounded
  fallback; dual failure returns `503` and does not reach business handlers.
- The local WAF-equivalent policy rejects request-smuggling ambiguity, duplicate
  authority/length headers, traversal encodings, control characters, unsupported
  methods, excessive request measurements, and non-JSON body-bearing commands.
  Unknown-length command bodies are read once into a bounded replay buffer;
  over-limit streams fail with `413` before a business handler executes.
- `scripts/supply-chain.ps1` generates a CycloneDX 1.6 SBOM from the resolved
  Maven tree, `uv.lock`, and npm lockfile. CI resolves all Compose OCI registry
  manifests and emits a content-addressed in-toto/SLSA provenance statement.
  The bundle is validated and retained as a GitHub Actions artifact for 30 days.
- Existing tracked-secret, key-extension, provider-token, workflow-permission,
  lockfile, Compose tag/loopback, and placeholder checks remain mandatory.

## Local validation

- `./scripts/business-api.ps1 -Action test`: 102 tests passed, 0 failures,
  0 errors, 0 skipped. New coverage includes tenant/role/actor/route key
  separation, quota metadata, normalized aggregate routes, structural firewall
  negatives, bounded unknown-length bodies, primary failure fallback, dual
  failure close, counter-key exhaustion/reclamation, property validation, and
  OIDC-chain integration.
- `./scripts/supply-chain.ps1`: passed generation and validation against three
  live Compose registry manifests. The local bundle has 527 components: 226
  Maven, 64 PyPI, 234 npm, and three OCI. SBOM SHA-256 is
  `a4b65b3b4c2cd792e5c1aa0dbece9cb0a1fe71d7440d035ff90058df4489cbd1`;
  provenance SHA-256 is
  `cd9784e3ef37a9e1319e841976930e4b7bdfd07bbc416cb85d03df8dd8cee878`.
  The source revision is the entry revision and `signed=false` is explicit.
- Supply-chain generator tests: 3 passed. Security-gate tests: 4 passed. The
  full repository control gate and local Compose configuration validation pass.
- Remote artifact validation remains pending until the implementation commit
  completes real GitHub Actions.

## CI remediation

- Initial implementation `b63f7b98cb4c65632eb046666447df24413860ad`
  entered Actions run `32818303442`. Control, Python, Web, and resilience jobs
  passed; the Java job failed before artifact upload.
- The job log proved that the non-executable POSIX `mvnw` had been handed to
  `xdg-open`, and the PowerShell entrypoint did not propagate that non-execution
  as failure. Consequently the supply-chain generator correctly failed closed
  on a missing Maven tree. This run is not completion evidence.
- Both Java and supply-chain entrypoints now launch the POSIX wrapper explicitly
  through `bash`. The security gate includes a directed negative test that
  rejects a launcher without that explicit execution path. A clean replacement
  Actions run and its retained artifact remain required.

## Claim boundary

The current limiter is a bounded per-instance adapter, not proof of fleet-wide
atomic quotas. The WAF evidence is the tested local equivalent, not a managed
vendor deployment. Generated provenance explicitly records `signed=false` and
does not claim registry signing, vulnerability freshness, penetration testing,
production traffic, or deployment. R3-325 remains frozen and was not rerun.
