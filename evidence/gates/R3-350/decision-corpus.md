# R3-350 Privacy-Bounded Decision Corpus

Date: 2026-08-24
Status: passed
Implementation checkpoint: `15c29feefcd10f1644b03899dab9e8f4fa6329d8a`
GitHub Actions: PASS - run `32739524990` (Java, Python/contracts, Web/browser,
control-plane/Compose, and bounded degradation/resilience jobs)

## Executable evidence

- `./scripts/compute-api.ps1 -Action check`
  - Ruff check and format, strict mypy, and contract validation passed.
  - 766 Python tests passed with 95.11% total coverage.
  - Determinism, analytical archive, analytical mart, and semantic-metrics gates passed.
- `routemind-decision-corpus --input docs/research/r3/manifests/decision-corpus/r3-350-fixture.json --data-root F:\Projects\RouteMind-Data`
  - built two records without replaying, executing, or sampling production traffic;
  - read-only reload verified both JSONL and manifest SHA-256 sidecars;
  - rerunning the same input is idempotent, while changed content is rejected by
    write-once checks.
- `tests/test_decision_corpus.py`: 7 directed tests cover deterministic ordering,
  all required linkage, forbidden raw-field rejection, missing/duplicate/action
  failures, checksum tampering, write-once collision, non-finite values, and the CLI.

## Retention and lineage boundary

The allow-list preserves `decision_id`, state digest/version, strategy/version,
candidate summaries, selected action, alternatives and rejection codes, objective
and risk summaries, verification checks, reference-data identity/version/digest,
clock domain/time/sequence, source-event digest, and outcome linkage. Candidate
payloads are summaries only; coordinates, trajectories, raw payloads, addresses,
direct identifiers, and recursive variants of those fields are rejected before
normalization. Java remains the durable dispatch ledger owner; this Python artifact
is a research read model and cannot mutate dispatch state.

The committed synthetic source manifest is
`docs/research/r3/manifests/decision-corpus/r3-350-source-manifest-v1.json` with
SHA-256 `b5201a9b37bd6a23ac63bfecd110232e6b93ba02a613dcd891eb77e8847a1cb7`.
The generated artifact is outside Git at
`F:\Projects\RouteMind-Data\research\r3\R3-350\r3-350-fixture-20260824`:

- manifest digest: `d92c58cbf196e3f9ab7a157e575831f4c35a9508d3482a6f6ba90728c89e569b`
- records SHA-256: `cc7e64cfa820a93c90d4cf4c070cd91ac35d8fa48d6a4a2e59d535cd3a7cfb38`
- records digest: `a9fbc9d01cf8bddff917e3b067342b091877bc24cbabbf9e776cc8e74e06799f`
- record count: 2; files: `manifest.json`, `manifest.json.sha256`,
  `records.jsonl`, `records.jsonl.sha256`

## Claim boundary

R3-350 is research infrastructure. It establishes a reproducible, privacy-bounded
corpus only; it is not a dispatch-quality result, an OPE identifiability result,
or a scientific effect. R3-350 closes `E-PASS / X-NOT-REQUIRED /
S-NOT-APPLICABLE / C-NOT-APPLICABLE`. R3-354 must audit support and propensities
before any off-policy claim is considered, and no propensity is fabricated here.
