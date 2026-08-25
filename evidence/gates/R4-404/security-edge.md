# R4-404 Edge Security and Supply-Chain Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `00c2706bb55abacd089ed83e9fc5a616763b66db`

Status: passed - `CI_VALIDATED`

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
  rejects a launcher without that explicit execution path.
- Replacement revision `0ff56158cac1fba550b5b0b4a22cc4c236ad2bbe`
  entered run `32818849130` and proved all 102 Java tests actually executed. It
  exposed 15 order-dependent H2 errors after `TenantIsolationIntegrationTests`
  dirtied a shared Spring context on Linux; the other four jobs passed.
- The tenant-isolation suite now binds its own H2 database before dirtying its
  context. A forced reverse-alphabetical regression ran that suite before the
  business integration suite and passed 20/20. The clean replacement Actions
  and retained-artifact requirements were subsequently satisfied below.

## Remote closure

- Final remediation revision:
  `f6d8ef03b91b57d5753c87f7fbc55b16784286c8`.
- GitHub Actions run `32819593245`: all five jobs passed. The Java job truly
  executed 102 tests before generating and uploading the evidence bundle.
- Artifact: `r4-404-supply-chain-f6d8ef03b91b57d5753c87f7fbc55b16784286c8`,
  artifact ID `9552635104`, 68,966 bytes, retained through 2026-09-24. GitHub
  artifact digest is
  `sha256:a25a93d0e7d47d15b5d4d04be99dce9df3623eeb11ed043124bac64e87f2f860`.
- The downloaded bundle passed the repository validator. It binds source
  revision `f6d8ef03b91b57d5753c87f7fbc55b16784286c8`, 527 components
  (226 Maven, 64 PyPI, 234 npm, three OCI), and the three declared Compose
  images. Remote SBOM SHA-256 is
  `6d8761909eb55a44d74d41fb6e322ae09a75a780384b957e231f9558b9b04cd7`;
  remote provenance SHA-256 is
  `7ecd82bffbce5dc966147a238c62083f912ecd55e072fccc11a87a78af750864`.
  `signed=false` remains explicit.

## Claim boundary

The current limiter is a bounded per-instance adapter, not proof of fleet-wide
atomic quotas. The WAF evidence is the tested local equivalent, not a managed
vendor deployment. Generated provenance explicitly records `signed=false` and
does not claim registry signing, vulnerability freshness, penetration testing,
production traffic, or deployment. R3-325 remains frozen and was not rerun.
