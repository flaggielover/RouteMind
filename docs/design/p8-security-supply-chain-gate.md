# P8 Security and Supply-Chain Hygiene Gate

## Goal

Add a local, deterministic repository gate for secret isolation and basic
dependency, container, and workflow hygiene. It is deliberately narrower than a
production penetration test or vulnerability database scan, so missing paid
services or network access cannot block the repository safety baseline.

## Checks

`scripts/security_gate.py` reads Git-tracked files only and verifies:

- no private-key blocks, high-confidence provider tokens, or sensitive key-file
  extensions are committed;
- `.env` is ignored and `.env.example` is present; local placeholder values are
  explicitly allowed while non-placeholder secret assignments are rejected;
- Python `uv.lock` and web `package-lock.json` exist, are parseable, and carry
  their expected lockfile metadata;
- every workflow declares read-only repository permissions and does not request
  write-all, `id-token`, or pull-request write access;
- Compose images are pinned away from `latest`, service ports bind to loopback,
  and development credentials retain the explicit local-only placeholder.

The gate reports file and line context for failures and is invoked by the
repository control gate. It does not claim dependency CVE freshness, SBOM
completeness, production identity/authentication, or runtime container hardening.
